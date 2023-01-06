# johnnydmad-www
 website & preview generator script for johnnydmad

## instructions:
- by default, this script expects johnnydmad to be located at ../johnnydmad and the target website repository at ../emberling.github.io -- edit `pages.cfg` to adjust the former and `make.bat` to change the latter
- you must also provide a FF6 ROM as ff6.smc in the script's directory
- `generate.py` will create all SPC previews and all the necessary html
- edit `pages.cfg` to change the source directories, samples, page names & descriptions, etc
- You can use `generate.py pagename` to generate only one page at a time
- You can also use `generate.py pagename songname` when adding or revising a single song. This will skip the SPC generation and duration tracing steps for all other songs, which basically means you're only spending time processing the one selected song. However, if any songs other than the specified songname lack an SPC file, it will fail.
- You can also use `generate.py pagename nonsense` to re-generate the page in question without doing any SPC generation or duration tracing.
- `make.bat` is available to automate copying the generated pages to the website repository. It is not intelligently generated at this time so if you edit `pages.cfg` to add/remove/rename pages then you will also have to edit this.