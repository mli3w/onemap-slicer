# OneMap API Reference

Complete API documentation from https://www.onemap.gov.sg/apidocs/

## Base URL

```
https://www.onemap.gov.sg/api
```

## Authentication

All APIs (except map tiles) require token-based authentication.

### Get Token

```
POST /api/auth/post/getToken
```

**Request Body:**
```json
{
  "email": "your-registered-email@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiry_timestamp": "1689388144"
}
```

**Notes:**
- Token valid for 3 days
- Expiry timestamp in UNIX format
- Register at https://www.onemap.gov.sg/apidocs/register

**Usage:**
```javascript
fetch(url, {
  headers: {
    'Authorization': `${accessToken}`
  }
})
```

---

## Search API

Search for addresses, buildings, roads, postal codes.

### Search

```
GET /api/common/elastic/search
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| searchVal | Yes | Search query (building name, road, postal code) |
| returnGeom | Yes | Y/N - Return geometry coordinates |
| getAddrDetails | Yes | Y/N - Return address details |
| pageNum | No | Page number for pagination |

**Example:**
```
GET /api/common/elastic/search?searchVal=Marina+Bay+Sands&returnGeom=Y&getAddrDetails=Y&pageNum=1
```

**Response:**
```json
{
  "found": 14,
  "totalNumPages": 2,
  "pageNum": 1,
  "results": [
    {
      "SEARCHVAL": "MARINA BAY SANDS",
      "BLK_NO": "1",
      "ROAD_NAME": "BAYFRONT AVENUE",
      "BUILDING": "MARINA BAY SANDS",
      "ADDRESS": "1 BAYFRONT AVENUE MARINA BAY SANDS SINGAPORE 018971",
      "POSTAL": "018971",
      "X": "31059.46",
      "Y": "29543.38",
      "LATITUDE": "1.28345419690844",
      "LONGITUDE": "103.860809048956"
    }
  ]
}
```

---

## Reverse Geocode API

Get address from coordinates.

### Reverse Geocode (WGS84)

```
GET /api/public/revgeocode
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| location | Yes | Latitude,Longitude in WGS84 |
| buffer | No | 0-500 meters radius |
| addressType | No | HDB or All |

**Example:**
```
GET /api/public/revgeocode?location=1.3254295,103.9005321&buffer=40&addressType=All
```

### Reverse Geocode (SVY21)

```
GET /api/public/revgeocodexy
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| location | Yes | X,Y in SVY21 format |
| buffer | No | 0-500 meters |
| addressType | No | HDB or All |

---

## Routing API

Calculate routes between points.

### Public Transport Routing

```
GET /api/public/routingsvc/route
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| start | Yes | Start lat,lng (WGS84) |
| end | Yes | End lat,lng (WGS84) |
| routeType | Yes | `pt` for public transport |
| date | Yes | MM-DD-YYYY format |
| time | Yes | HH:MM:SS (24-hour) |
| mode | Yes | TRANSIT, bus, or rail |
| maxWalkDistance | No | Max walking distance in meters |
| numItineraries | No | 1-3, number of route options |

**Example:**
```
GET /api/public/routingsvc/route?start=1.3081592,103.8551479&end=1.2739864,103.8012642&routeType=pt&date=01-26-2026&time=11:00:00&mode=TRANSIT
```

### Walk/Drive/Cycle Routing

```
GET /api/public/routingsvc/route
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| start | Yes | Start lat,lng (WGS84) |
| end | Yes | End lat,lng (WGS84) |
| routeType | Yes | `walk`, `drive`, or `cycle` |

**Response includes:**
- `route_geometry` - Encoded polyline
- `route_instructions` - Turn-by-turn directions
- `route_summary` - Total time (seconds), distance (meters)

---

## Coordinate Converters API

Convert between coordinate systems.

### Available Conversions

| Endpoint | From | To |
|----------|------|-----|
| `/api/common/convert/4326to3857` | WGS84 (lat/lng) | Web Mercator (X/Y) |
| `/api/common/convert/4326to3414` | WGS84 (lat/lng) | SVY21 (X/Y) |
| `/api/common/convert/3414to3857` | SVY21 (X/Y) | Web Mercator (X/Y) |
| `/api/common/convert/3414to4326` | SVY21 (X/Y) | WGS84 (lat/lng) |
| `/api/common/convert/3857to3414` | Web Mercator (X/Y) | SVY21 (X/Y) |
| `/api/common/convert/3857to4326` | Web Mercator (X/Y) | WGS84 (lat/lng) |

**Example (WGS84 to SVY21):**
```
GET /api/common/convert/4326to3414?latitude=1.319728905&longitude=103.8421581
```

**Response:**
```json
{
  "Y": 33554.4360965479,
  "X": 28983.75169436287
}
```

---

## Themes API

Access 100+ thematic layers (schools, clinics, parks, etc.)

### Get All Themes

```
GET /api/public/themesvc/getAllThemesInfo?moreInfo=Y
```

**Response:**
```json
{
  "Theme_Names": [
    {
      "THEMENAME": "Kindergartens",
      "QUERYNAME": "kindergartens",
      "ICON": "school.gif",
      "CATEGORY": "Education",
      "THEME_OWNER": "EARLY CHILDHOOD DEVELOPMENT AGENCY"
    }
  ]
}
```

### Retrieve Theme Data

```
GET /api/public/themesvc/retrieveTheme?queryName=kindergartens
```

### Retrieve Theme with Bounds

```
GET /api/public/themesvc/retrieveTheme?queryName=dengue_cluster&extents=1.291789,103.7796402,1.3290461,103.8726032
```

---

## Planning Area API

Singapore's 55 URA planning areas.

### Get All Planning Area Polygons

```
GET /api/public/popapi/getAllPlanningarea?year=2019
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| year | No | 1998, 2008, 2014, 2019 (default: latest) |

### Get Planning Area Names

```
GET /api/public/popapi/getPlanningareaNames?year=2019
```

### Query Planning Area by Location

```
GET /api/public/popapi/getPlanningArea?location=1.3,103.8
```

---

## Population Query API

Demographics by planning area from Department of Statistics.

### Available Endpoints

| Endpoint | Data |
|----------|------|
| `/api/public/popapi/getEconomicStatus` | Economic status |
| `/api/public/popapi/getEducationAttending` | Education status |
| `/api/public/popapi/getEthnicGroup` | Ethnic distribution |
| `/api/public/popapi/getHouseholdMonthlyIncomeWork` | Household income |
| `/api/public/popapi/getHouseholdSize` | Household size |
| `/api/public/popapi/getHouseholdStructure` | Household structure |
| `/api/public/popapi/getIncomeFromWork` | Work income |
| `/api/public/popapi/getIndustry` | Industry |
| `/api/public/popapi/getLanguageLiterate` | Language literacy |
| `/api/public/popapi/getMaritalStatus` | Marital status |
| `/api/public/popapi/getModeOfTransportSchool` | Transport to school |
| `/api/public/popapi/getModeOfTransportWork` | Transport to work |
| `/api/public/popapi/getPopulationAgeGroup` | Age groups |
| `/api/public/popapi/getReligion` | Religion |
| `/api/public/popapi/getSpokenAtHome` | Spoken language |
| `/api/public/popapi/getTenancy` | Tenancy |
| `/api/public/popapi/getDwellingType` | Dwelling type |

**Common Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| planningArea | Yes | Planning area name |
| year | Yes | Data year |
| gender | No | male or female |

---

## Static Map API

Generate static map images.

```
GET /api/staticmap/getStaticImage
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| layerchosen | Yes | default, night, grey, original, landlot |
| latitude | Yes* | WGS84 latitude |
| longitude | Yes* | WGS84 longitude |
| postal | Yes* | Postal code (*either lat/lng or postal) |
| zoom | Yes | 11-19 |
| width | Yes | 128-512 pixels |
| height | Yes | 128-512 pixels |
| points | No | Point markers |
| lines | No | Polylines |
| polygons | No | Polygon overlays |
| color | No | Line color (RGB) |
| fillColor | No | Polygon fill (RGB) |

**Example:**
```
GET /api/staticmap/getStaticImage?layerchosen=default&latitude=1.31955&longitude=103.84223&zoom=17&width=400&height=400
```

---

## Map Tiles (No Auth Required)

### 2D Basemap Tiles

```
https://www.onemap.gov.sg/maps/tiles/{style}/{z}/{x}/{y}.png
```

**Styles:**
- `Default` - Standard map
- `Default_HD` - High-definition
- `Grey` - Grayscale
- `Night` - Dark mode
- `Original` - Classic style

**Example:**
```
https://www.onemap.gov.sg/maps/tiles/Default/18/206697/130135.png
```

### 3D Tiles (Cesium)

```
https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/tileset.json
```

B3DM tiles containing 3D building geometry.

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request / Invalid parameters |
| 401 | Token expired or invalid |
| 403 | Access forbidden |
| 404 | Resource not found |
| 429 | API rate limit exceeded |

---

## Rate Limits

- API calls are rate-limited
- Register for higher quotas
- Contact onemap@sla.gov.sg for enterprise access

---

## EPSG Codes Reference

| EPSG | Name | Description |
|------|------|-------------|
| 4326 | WGS84 | GPS coordinates (lat/lng) |
| 3414 | SVY21 | Singapore local projection (X/Y) |
| 3857 | Web Mercator | Web map standard (meters) |

---

## Resources

- [Register](https://www.onemap.gov.sg/apidocs/register)
- [API Terms of Use](https://www.onemap.gov.sg/termsofuse)
- [Singapore Open Data License](https://data.gov.sg/open-data-licence)
- [Contact](mailto:onemap@sla.gov.sg)
