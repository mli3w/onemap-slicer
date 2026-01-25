#!/usr/bin/env python3
"""
OneMap 3D Printer CLI Tool

Extract 3D building models from OneMap Singapore and export them
as print-ready 3MF/STL files for Bambu Studio.
"""

import argparse
import os
import sys
import tempfile

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from onemap_slicer.b3dm_parser import (
    extract_glb,
    extract_metadata,
    get_batch_table_summary,
    get_building_names,
    parse_header,
)
from onemap_slicer.exporter import export_mesh, get_export_info
from onemap_slicer.mesh_processor import (
    decompress_draco,
    get_mesh_info,
    isolate_building,
    load_mesh,
    prepare_for_print,
)
from onemap_slicer.onemap_api import (
    find_tiles,
    get_tile_data,
    load_tileset,
    search_buildings,
)

# Initialize rich console for colored output
console = Console()


def is_interactive() -> bool:
    """Check if running in interactive mode (TTY)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def parse_scale(scale_str: str) -> float:
    """
    Parse scale argument.

    Accepts:
    - Decimal: 0.001
    - Ratio: 1:1000

    Returns scale factor to multiply coordinates by.
    """
    if ":" in scale_str:
        parts = scale_str.split(":")
        if len(parts) == 2:
            try:
                num = float(parts[0])
                denom = float(parts[1])
                return num / denom
            except ValueError:
                pass
        raise ValueError(f"Invalid scale ratio: {scale_str}")

    try:
        return float(scale_str)
    except ValueError as e:
        raise ValueError(f"Invalid scale value: {scale_str}") from e


def print_status(message: str, symbol: str = "→"):
    """Print a status message."""
    console.print(f"  [dim]{symbol}[/dim] {message}")


def print_error(message: str):
    """Print an error message."""
    console.print(f"  [red]✗[/red] Error: {message}", style="red")


def print_success(message: str):
    """Print a success message."""
    console.print(f"  [green]✓[/green] {message}")


def display_search_results_table(results: list[dict]):
    """Display search results in a rich table."""
    table = Table(
        title="Search Results",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        width=console.width if console.width else 100,
    )

    table.add_column("Idx", style="dim", width=4, justify="right")
    table.add_column("Name", style="bold", min_width=20, max_width=35, overflow="fold")
    table.add_column("Address", min_width=25, max_width=45, overflow="fold")
    table.add_column("Postal", width=8, justify="center")

    for i, result in enumerate(results):
        table.add_row(
            str(i),
            result["name"],
            result["address"],
            result["postal"],
        )

    console.print()
    console.print(table)
    console.print()


def select_search_result(results: list[dict]) -> int:
    """Interactive selection of search result using questionary."""
    import questionary

    choices = []
    for i, result in enumerate(results):
        # Format: "[0] BUILDING NAME (POSTAL)"
        postal = f" ({result['postal']})" if result["postal"] else ""
        label = f"[{i}] {result['name']}{postal}"
        choices.append(questionary.Choice(title=label, value=i))

    selected = questionary.select(
        "Select a building:",
        choices=choices,
        use_indicator=True,
        use_shortcuts=False,
    ).ask()

    if selected is None:
        # User cancelled (Ctrl+C)
        return -1

    return selected


def display_buildings_table(metadata: dict, debug: bool = False):
    """Display buildings found in tile metadata as a rich table."""
    names = get_building_names(metadata)
    batch_count = metadata.get("batch_count", 0)
    batch_table = metadata.get("batch_table", {})

    # Try to get heights if available
    heights = batch_table.get("height", batch_table.get("HEIGHT", []))

    table = Table(
        title=f"Buildings in Tile ({batch_count} total)",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        width=console.width if console.width else 100,
    )

    table.add_column("Idx", style="dim", width=4, justify="right")
    table.add_column("Building Name", style="bold", min_width=30, max_width=50, overflow="fold")

    if heights:
        table.add_column("Height", width=10, justify="right")

    if names:
        for i, name in enumerate(names):
            row = [str(i), name]
            if heights and i < len(heights):
                height_val = heights[i]
                if isinstance(height_val, (int, float)):
                    row.append(f"{height_val:.1f}m")
                else:
                    row.append(str(height_val))
            elif heights:
                row.append("-")
            table.add_row(*row)
    else:
        table.add_row("-", "[dim]No building names found in metadata[/dim]")

    console.print()
    console.print(table)

    if not names:
        console.print("  [dim](Buildings may still exist but without name attributes)[/dim]")

    # Show other batch table attributes
    other_attrs = [k for k in batch_table if k.lower() not in ["name", "building_name", "height"]]
    if other_attrs:
        console.print(f"\n  [dim]Other attributes: {', '.join(other_attrs)}[/dim]")

    # In debug mode, show detailed batch table summary
    if debug:
        console.print("\n  [bold]Batch table details:[/bold]")
        summary = get_batch_table_summary(metadata)
        for key, info in summary.items():
            if "sample" in info:
                sample_str = ", ".join(str(s) for s in info["sample"][:3])
                console.print(
                    f"    [cyan]{key}[/cyan]: [{info['count']} items] samples: {sample_str}"
                )
            else:
                console.print(f"    [cyan]{key}[/cyan]: {info['value']}")

    console.print()


def select_building(metadata: dict) -> int:
    """Interactive selection of a building from tile metadata."""
    import questionary

    names = get_building_names(metadata)
    if not names:
        console.print("[yellow]No building names available for selection.[/yellow]")
        return -1

    choices = []
    for i, name in enumerate(names):
        label = f"[{i}] {name}"
        choices.append(questionary.Choice(title=label, value=i))

    selected = questionary.select(
        "Select a building to export:",
        choices=choices,
        use_indicator=True,
        use_shortcuts=False,
    ).ask()

    if selected is None:
        return -1

    return selected


def main():
    parser = argparse.ArgumentParser(
        prog="onemap-slicer",
        description="Extract 3D building models from OneMap Singapore for 3D printing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Marina Bay Sands" -o mbs.3mf
  %(prog)s "UOB Plaza" --scale 1:500 --format stl
  %(prog)s "018956" --list
  %(prog)s "Tanjong Pagar" --result-index 0 --no-interactive
  %(prog)s "UOB Plaza" --building-index 0 -o uob.3mf
        """,
    )

    parser.add_argument(
        "query",
        help="Building name, address, or postal code",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="building.3mf",
        help="Output file path (default: building.3mf)",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["3mf", "stl"],
        default="3mf",
        help="Output format (default: 3mf)",
    )

    parser.add_argument(
        "-s",
        "--scale",
        default="1:1000",
        help="Scale factor or ratio (default: 1:1000)",
    )

    parser.add_argument(
        "--lod",
        choices=["low", "medium", "high"],
        default="high",
        help="Level of detail (default: high)",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List buildings in tile (don't export)",
    )

    parser.add_argument(
        "--list-results",
        action="store_true",
        help="List all search results and exit",
    )

    parser.add_argument(
        "--result-index",
        type=int,
        default=None,
        metavar="N",
        help="Select Nth search result (skips interactive menu)",
    )

    parser.add_argument(
        "--building-index",
        type=int,
        default=None,
        metavar="N",
        help="Export only Nth building from tile",
    )

    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable interactive menus (for scripts/CI)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information",
    )

    args = parser.parse_args()

    # Determine if we can use interactive mode
    interactive = is_interactive() and not args.no_interactive

    # Parse scale
    try:
        scale = parse_scale(args.scale)
    except ValueError as e:
        print_error(str(e))
        return 1

    console.print()
    console.print("[bold]OneMap 3D Building Extractor[/bold]")
    console.print("[dim]" + "=" * 40 + "[/dim]")

    # Step 1: Search for building
    console.print(f"\n[bold]Searching for:[/bold] {args.query}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Searching OneMap...", total=None)
        results = search_buildings(args.query)

    if not results:
        print_error(f"No results found for '{args.query}'")
        return 1

    # List results mode - show all results and exit
    if args.list_results:
        display_search_results_table(results)
        return 0

    # Select search result
    if len(results) == 1:
        # Only one result, use it
        location = results[0]
    elif args.result_index is not None:
        # Use specified index
        if args.result_index >= len(results):
            print_error(
                f"Result index {args.result_index} out of range (found {len(results)} results)"
            )
            display_search_results_table(results)
            return 1
        location = results[args.result_index]
    elif interactive and len(results) > 1:
        # Show interactive selection
        display_search_results_table(results)
        selected_idx = select_search_result(results)
        if selected_idx < 0:
            console.print("[yellow]Selection cancelled.[/yellow]")
            return 1
        location = results[selected_idx]
    else:
        # Non-interactive with multiple results - use first and show warning
        location = results[0]
        if len(results) > 1:
            console.print(
                f"[yellow]Multiple results found ({len(results)}). Using first result.[/yellow]"
            )
            console.print(
                "[dim]Use --result-index N or --list-results to select a specific result.[/dim]"
            )

    print_success(f"Found: {location['name']}")
    print_status(f"Address: {location['address']}")
    print_status(f"Coordinates: {location['lat']:.6f}, {location['lng']:.6f}")

    # Step 2: Load tileset
    console.print("\n[bold]Loading 3D tileset...[/bold]")
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Fetching tileset.json...", total=None)
            tileset = load_tileset()
        print_success("Tileset loaded")
    except Exception as e:
        print_error(f"Failed to load tileset: {e}")
        return 1

    # Step 3: Find matching tiles
    console.print("\n[bold]Finding tiles at location...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Traversing tileset tree...", total=None)
        tiles = find_tiles(tileset, location["lat"], location["lng"])

    if not tiles:
        print_error("No tiles found at this location")
        return 1

    print_success(f"Found {len(tiles)} matching tile(s)")

    # Select tile based on LOD preference
    # Tiles are sorted by geometric error ascending (lower error = more detail)
    # So index 0 = highest detail, index -1 = lowest detail
    lod_index = {"high": 0, "medium": len(tiles) // 2, "low": -1}[args.lod]
    selected_tile = tiles[lod_index]

    print_status(f"Using tile with geometric error: {selected_tile['geometricError']:.2f}")

    if args.debug:
        print_status(f"Tile URI: {selected_tile['uri']}")

    # Step 4: Download tile data
    console.print("\n[bold]Downloading tile data...[/bold]")
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Downloading...", total=None)
            tile_data = get_tile_data(selected_tile["uri"])
            progress.update(task, completed=True)
        print_success(f"Downloaded {len(tile_data):,} bytes")
    except Exception as e:
        print_error(f"Failed to download tile: {e}")
        return 1

    # Step 5: Parse B3DM
    console.print("\n[bold]Parsing B3DM format...[/bold]")
    try:
        header = parse_header(tile_data)
        metadata = extract_metadata(tile_data, header)
        glb_data = extract_glb(tile_data, header)
        print_success(f"Extracted GLB: {len(glb_data):,} bytes")
        print_status(f"Batch count: {metadata.get('batch_count', 'unknown')}")
    except Exception as e:
        print_error(f"Failed to parse B3DM: {e}")
        return 1

    # Track which building to isolate (if any)
    building_to_isolate = args.building_index

    # List mode - show buildings and optionally offer selection
    if args.list:
        display_buildings_table(metadata, debug=args.debug)

        # In interactive mode, offer to export a building
        if interactive and building_to_isolate is None:
            import questionary

            proceed = questionary.confirm(
                "Would you like to export a specific building?",
                default=False,
            ).ask()

            if proceed:
                building_to_isolate = select_building(metadata)
                if building_to_isolate < 0:
                    return 0
                # Continue to export below
            else:
                return 0
        else:
            return 0

    # Step 6: Save GLB and process mesh
    console.print("\n[bold]Processing mesh...[/bold]")

    with tempfile.TemporaryDirectory() as tmpdir:
        glb_path = os.path.join(tmpdir, "tile.glb")
        decompressed_path = os.path.join(tmpdir, "tile_decompressed.glb")

        # Write GLB to temp file
        with open(glb_path, "wb") as f:
            f.write(glb_data)

        # Attempt Draco decompression
        print_status("Checking for Draco compression...")
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Decompressing mesh...", total=None)
                decompressed_path = decompress_draco(glb_path, decompressed_path)
            print_success("Mesh processed")
        except Exception as e:
            print_status(f"Using original GLB (decompression skipped: {e})")
            decompressed_path = glb_path

        # Load mesh
        print_status("Loading mesh...")
        try:
            mesh = load_mesh(decompressed_path)
        except Exception as e:
            print_error(f"Failed to load mesh: {e}")
            return 1

        # Determine building name for export metadata
        export_building_name = location["name"]

        # Isolate specific building if requested
        if building_to_isolate is not None:
            building_names = get_building_names(metadata)
            if building_to_isolate < len(building_names):
                export_building_name = building_names[building_to_isolate]
                print_status(f"Isolating building: {export_building_name}")
            else:
                print_status(f"Isolating building at index: {building_to_isolate}")

            mesh = isolate_building(mesh, building_to_isolate)
            print_success("Building isolated")

        if args.debug:
            info = get_mesh_info(mesh)
            print_status(f"Mesh info: {info['vertices']} vertices, {info['faces']} faces")
            if info.get("bounds"):
                bounds = info["bounds"]
                size = [bounds[1][i] - bounds[0][i] for i in range(3)]
                print_status(f"Size (m): {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f}")

        # Step 7: Prepare for printing
        console.print("\n[bold]Preparing for 3D printing...[/bold]")
        print_status(f"Scale: {args.scale} ({scale})")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Repairing and scaling mesh...", total=None)
            mesh = prepare_for_print(mesh, scale=scale)
        print_success("Mesh prepared")

        if args.debug:
            info = get_mesh_info(mesh)
            if info.get("bounds"):
                bounds = info["bounds"]
                size = [bounds[1][i] - bounds[0][i] for i in range(3)]
                # Convert from meters to mm for display (coords are in meters after scaling)
                size_mm = [s * 1000 for s in size]
                print_status(
                    f"Final size (mm): {size_mm[0]:.1f} x {size_mm[1]:.1f} x {size_mm[2]:.1f}"
                )

        # Step 8: Export
        console.print(f"\n[bold]Exporting to {args.format.upper()}...[/bold]")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Writing file...", total=None)
                output_path = export_mesh(
                    mesh, args.output, args.format, building_name=export_building_name
                )
            export_info = get_export_info(output_path)
            print_success(f"Exported: {output_path}")
            print_status(f"File size: {export_info['size_human']}")
        except Exception as e:
            print_error(f"Failed to export: {e}")
            return 1

    console.print()
    console.print("[dim]" + "=" * 40 + "[/dim]")
    console.print(
        f"[green]Done![/green] Open [bold]{output_path}[/bold] in Bambu Studio to preview."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
