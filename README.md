# OneMap Slicer

Extract 3D building models from Singapore and export them as print-ready files for your 3D printer.

OneMap Slicer searches Singapore's [OneMap](https://www.onemap.gov.sg/) database, downloads 3D building models, and converts them to 3MF or STL files ready for slicing in Bambu Studio, PrusaSlicer, Cura, or any other slicer software.

## Features

- Search buildings by name, address, or postal code
- Interactive selection when multiple results match
- Export individual buildings from multi-building tiles
- Automatic mesh repair for watertight prints
- Configurable scale (default 1:1000)
- 3MF export with building names and attribution metadata

## Requirements

- **Python 3.10 or newer**
- **Node.js 18 or newer** (for mesh decompression)

<details>
<summary>Installing Python and Node.js</summary>

### macOS

```bash
brew install python node
```

### Windows

1. **Install Python** from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Install Node.js** from [nodejs.org](https://nodejs.org/)
   - Use the LTS version

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-pip

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install nodejs
```

### Linux (Fedora)

```bash
sudo dnf install python3 python3-pip nodejs
```

### Linux (Arch)

```bash
sudo pacman -S python python-pip nodejs npm
```

</details>

## Installation

```bash
pip install git+https://github.com/aniruddha-adhikary/onemap-slicer.git
```

## Quick Start

Search for a building and export it:

```bash
onemap-slicer "Marina Bay Sands" -o marina-bay-sands.3mf
```

The tool will:
1. Search OneMap for matching buildings
2. Show an interactive menu if multiple results exist
3. Download the 3D tile data
4. Extract and process the mesh
5. Export a print-ready file

## Usage Examples

### Basic Export

```bash
# Export Marina Bay Sands at 1:1000 scale
onemap-slicer "Marina Bay Sands" -o mbs.3mf

# Search by postal code
onemap-slicer "018956" -o building.3mf

# Search by address
onemap-slicer "10 Bayfront Avenue" -o bayfront.3mf
```

### List Search Results

See all matching buildings before choosing:

```bash
onemap-slicer "Tanjong Pagar" --list-results
```

### Select Specific Result

Skip the interactive menu by specifying which result to use:

```bash
onemap-slicer "Marina Bay" --result-index 0 -o marina.3mf
```

### List Buildings in a Tile

Some tiles contain multiple buildings. List them first:

```bash
onemap-slicer "UOB Plaza" --list
```

Output:
```
Buildings in tile:
  [0] UOB Plaza 1
  [1] UOB Plaza 2
  [2] OUB Centre
```

### Export Specific Building

Extract just one building from a multi-building tile:

```bash
onemap-slicer "UOB Plaza" --building-index 0 -o uob-plaza-1.3mf
```

### Change Scale

Adjust the model scale for your printer:

```bash
# 1:500 scale (larger print)
onemap-slicer "Marina Bay Sands" --scale 1:500 -o mbs-large.3mf

# 1:2000 scale (smaller print)
onemap-slicer "Marina Bay Sands" --scale 1:2000 -o mbs-small.3mf

# Decimal scale factor
onemap-slicer "Marina Bay Sands" --scale 0.002 -o mbs.3mf
```

### Non-Interactive Mode

For scripts or automation, disable interactive prompts:

```bash
onemap-slicer "Marina Bay" --result-index 0 --no-interactive -o output.3mf
```

## Command Reference

```
onemap-slicer QUERY [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-o, --output FILE` | Output file path (default: building.3mf) |
| `-f, --format FORMAT` | Output format: `3mf` or `stl` (default: 3mf) |
| `-s, --scale SCALE` | Scale as ratio (1:1000) or decimal (0.001) |
| `--lod LEVEL` | Detail level: `low`, `medium`, `high` (default: high) |
| `--list` | List buildings in tile without exporting |
| `--list-results` | List all search results and exit |
| `--result-index N` | Use Nth search result (0-based) |
| `--building-index N` | Export Nth building from tile (0-based) |
| `--no-interactive` | Disable interactive menus |
| `--debug` | Show detailed debug output |

## Troubleshooting

### "Node.js not found" or "npx not found"

The tool requires Node.js for mesh decompression. Install it:

- **macOS**: `brew install node`
- **Windows**: Download from [nodejs.org](https://nodejs.org/)
- **Linux**: Use your package manager or [NodeSource](https://github.com/nodesource/distributions)

After installing, restart your terminal.

### "No buildings found" for a search

Try different search terms:
- Use the full building name
- Try the street address
- Use the 6-digit postal code

### Large complex is incomplete

Large developments like Marina Bay Sands span multiple 3D tiles. Currently, the tool exports only the tile at the searched coordinates, so you may get partial buildings or only some towers. Multi-tile export is planned for a future release.

### Mesh has holes or issues

Some source models may have geometry issues. Try:
- Using a different `--lod` level
- Repairing the mesh in your slicer software
- Using MeshLab or Meshmixer to fix issues

### Permission denied when installing

**Linux/macOS**: Use `pip install --user git+https://github.com/aniruddha-adhikary/onemap-slicer.git` or set up a virtual environment.

**Windows**: Run PowerShell as Administrator, or use `pip install --user git+https://github.com/aniruddha-adhikary/onemap-slicer.git`.

### Slow first run

The first export downloads required dependencies automatically. Subsequent runs will be faster due to caching.

## Cache Location

Cached data is stored at:

- **macOS**: `~/Library/Caches/onemap-slicer/`
- **Linux**: `~/.cache/onemap-slicer/`
- **Windows**: `%LOCALAPPDATA%\onemap-slicer\Cache\`

Delete this folder to clear the cache.

## Tips for 3D Printing

1. **Use 3MF format**: Building names appear in your slicer, making it easy to identify models

2. **Scale selection**: At 1:1000 scale, a 200m tall building becomes 200mm (about 8 inches)

2. **Supports**: Most buildings will need supports for overhangs

3. **Orientation**: Buildings typically export upright, which is usually the best print orientation

4. **Infill**: 10-15% infill works well for display models

5. **Layer height**: 0.2mm works well; use 0.12mm for finer architectural details

## Attribution

Models exported by this tool contain attribution metadata crediting:
- Singapore Land Authority (SLA)
- OneMap Singapore

Please retain attribution when sharing or publishing printed models.

## STL Export (Legacy)

STL is supported for compatibility with older slicers that don't support 3MF. However, STL is a limited format that cannot store building names or rich metadata.

```bash
onemap-slicer "Marina Bay Sands" --format stl -o mbs.stl
```

If your slicer supports 3MF (Bambu Studio, PrusaSlicer, Cura, etc.), use 3MF instead.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Links

- [OneMap Singapore](https://www.onemap.gov.sg/)
- [Report Issues](https://github.com/aniruddha-adhikary/onemap-slicer/issues)
