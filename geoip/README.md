# GeoIP Database Directory

This directory contains the MaxMind GeoLite2-City database used for IP geolocation.

## Database Files

- **GeoLite2-City.mmdb.gz** (29MB) - Compressed MaxMind IP geolocation database
  - Automatically decompressed on first run
  - Used to convert IP addresses to geographic coordinates
  - Included in this repository (compressed to save space)

- **GeoLite2-City.mmdb** (60MB) - Uncompressed database (auto-generated)
  - Created automatically when you run the pipeline
  - Gitignored (too large to commit)

## How It Works

1. The compressed `.gz` file is included in the repository
2. On first run, the script automatically decompresses it
3. Subsequent runs use the decompressed `.mmdb` file
4. **No manual download or setup required!**

## License

This product includes GeoLite2 data created by MaxMind, available from [https://www.maxmind.com](https://www.maxmind.com).

See `LICENSE` file for full attribution.

## Updating the Database

MaxMind releases updated versions of GeoLite2 databases regularly. To update:

1. Download the latest GeoLite2-City database from MaxMind:
   - Visit: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
   - Sign up for a free account (required)
   - Download GeoLite2-City in MMDB format

2. Compress and replace:
   ```bash
   gzip -9 GeoLite2-City.mmdb
   mv GeoLite2-City.mmdb.gz geoip/
   ```



