# Nakama-DL

A specialized manga chapter downloader and PDF converter for One Piece chapters from One Piece Nakama (a website of Hebrew-translated One Piece chapters by fans) RSS feed. The tool generates PDF files with Komga-compatible naming conventions for seamless integration with your manga library.

## Description

Nakama-DL is an automated tool that monitors RSS feeds for new One Piece manga chapter releases, downloads them from Mega.nz links, and converts the images into high-quality PDF files. The tool is designed to run continuously, checking for new releases at configurable intervals. Generated PDFs follow Komga's naming conventions, allowing for direct integration with your Komga manga server without any manual renaming.

## Features

- 🔄 Automated RSS feed monitoring
- ⬇️ Automatic chapter detection and download from Mega.nz links
- 📑 Conversion of manga images to properly ordered PDF files
- 🔍 Smart chapter number detection from filenames
- 📱 Komga-compatible file naming (for a seamless integration with a Komga server)
- 📝 Comprehensive logging system
- ⚙️ Configurable settings via YAML
- 🔒 Download tracking to prevent duplicates

## Prerequisites

- Python 3.8 or higher
- UnRAR executable installed and accessible in PATH
- Access to Mega.nz (no account required)

### Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `rss_feed_url` | URL of the RSS feed to monitor. You can leave it as it is. | Required |
| `output_pdf_directory` | Directory where PDFs will be saved. Make sure it's the FULL path. Escape any "\\" using `\\` (if needed, for example when running on Windows) | Required |
| `chapter_keyword` | Keyword to identify chapter posts. You can leave it as it is. | `"צ'אפטר"` |
| `check_interval_minutes` | How often to check for new chapters posted on One Piece Nakama's website, in minutes. The recommeneded value is `60` minutes. | 60 |
| `max_age_hours` | Maximum age of posts to process. Posts of chapters before this time span won't be downloaded. The recommeneded value is `24`. | 24 |

## Usage

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nakama-dl.git
cd nakama-dl
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your `config.yml`

4. Run the script:
```bash
python main.py
```

## Error Handling

The script includes comprehensive error handling and logging:
- Failed downloads are retried on next cycle
- File access errors are handled gracefully
- All operations are logged with appropriate detail levels

## Komga Integration

Nakama-DL is designed to work seamlessly with [Komga](https://komga.org/), a free and open source manga server. The tool automatically generates PDF files following Komga's naming conventions:

- Files are named in the format: `One Piece - XXXX.pdf` (where XXXX is the chapter number)
- Chapter numbers are zero-padded for proper sorting
- Files are organized in a clean, Komga-friendly structure

To use with Komga:
1. Set your `output_pdf_directory` to a folder that Komga monitors
2. Komga will automatically detect new chapters as they're downloaded
3. Chapter numbers will be correctly parsed and organized in your library

This integration allows for a completely automated workflow from chapter release to reading in your Komga server.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

Guidelines:
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. Please support the official manga releases.
