# iGEM Wiki Template using Bootstrapped Middleman

This templates combines several tools for fast website development targeted to the iGEM wiki environment.

Tools included:

- Middleman (v4): For automatic static web page generation
- Bootstrap (v4.0-beta): CSS Framework to ease web design
- uploader script: For fast and easy page upload

Features:

- CSS Normalizer stylesheet to remove unwanted effects from the iGEM CSS Environment
- Local preview (including iGEM CSS environment)
- Upload fixes links to stylesheets and scripts (adding `&action=raw&ctype=text/<mime-type>`)

## Requirements

* Ruby and RubyGems
* Python (2.7 tested, 3 and above should work)
* Python packages: requests and beautifulsoup4
* XCode (macOS)

## Usage

1. Download (git clone) the repository.
2. In Terminal run `gem install bundler`
3. Move into the repository folder (e.g. `cd igem_template`)
4. Run `bundle install` (installs all ruby dependencies)
5. Run `pip install requests beautifulsoup4`

To build the site:

- `middleman build` (or `bundle exec middleman build`)

To preview the site:

- `middleman server` (or `bundle exec middleman server`)

To upload the site (after building):

1. Create an ini file (`igem.ini` for example):

```ini
username: <igem username>
password: <igem password>
team: <igem team name>
strip: 1
# in case you want to upload to a specific location
# Example: 'Team:Name/index` => 'Team:Name/prefix/index'
# Uncomment the following:
#prefix: prefix
``` 

2. Run the upload script:

`igem_upload.py --ini igem.ini upload "./build/*`"

This will upload all files in the build directory to the iGEM Wiki.

NOTE: The quotes around the file pattern may be necessary to prevent the terminal from expanding it before passing it
 to Python.

## TODO's

- Implement image uploading
- Implement 
