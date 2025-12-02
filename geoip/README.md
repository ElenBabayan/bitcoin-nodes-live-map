# GeoIP Database Directory

This directory contains the MaxMind GeoLite2-City database used for IP geolocation.

## Database File

- **GeoLite2-City.mmdb** (60MB) - MaxMind IP geolocation database
  - Used to convert IP addresses to geographic coordinates
  - Already included in this repository
  - Updated periodically (see below)

## License

This product includes GeoLite2 data created by MaxMind, available from [https://www.maxmind.com](https://www.maxmind.com).

See `LICENSE` file for full attribution.

## Updating the Database

MaxMind releases updated versions of GeoLite2 databases regularly. To update:

1. Download the latest GeoLite2-City database from MaxMind:
   - Visit: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
   - Sign up for a free account (required)
   - Download GeoLite2-City in MMDB format

2. Replace the existing file:
   ```bash
   cp /path/to/downloaded/GeoLite2-City.mmdb geoip/
   ```

Note: The .mmdb file is ignored by git (too large), so you'll need to keep it locally.

