import configparser
import os
import re
import subprocess
import sys
from glob import glob
from mfvitools.mml2mfvi import byte_insert, mml_to_akao, get_variant_list
from mfvitools.mfvitrace import mfvi_trace

ROM = "ff6.smc"
TEMPLATE_HTML = "templatehtml.template"
DURATION_INCLUDE_FADE = True

with open(TEMPLATE_HTML, "r") as f:
    template = f.read()

split_marker = "<!-- TEMPLATE -->"    
split_loc = template.find(split_marker)
head = template[:split_loc]
foot = template[split_loc + len(split_marker):]

def abort(msg):
    print()
    print(f"Aborting operation due to an error:")
    print(msg)
    input("Press enter to close.")
    quit()
    
def text_insert(data, position, text, length):
    new_data = bytearray(length)
    new_data = byte_insert(new_data, 0, bytes(text, "utf-8"), maxlength = length)
    return bytearray(byte_insert(data, position, new_data))
    
def table_row(data, head=False):
    row = "<tr>\n"
    cell = "th" if head else "td"
    for d in data:
        row += f"<{cell}>{d}</{cell}>\n"
    row += "</tr>\n"
    return row
    
class Track():
    def __init__(self, basefile, seqfile, spcfile, remote=None, variant=None):
    
        mml = None
        while not mml:
            try:
                with open(seqfile, "r") as f:
                    mml = f.read() + "\n"
            except IOError:
                if basefile.count('_') > 1:
                    seqfile, ext = os.path.splitext(seqfile)
                    seqfile, newvar = seqfile.rsplit('_', 1)
                    variant = '_'.join(variant, newvar) if variant else newvar
                    basefile = os.path.basename(seqfile)
                    seqfile += ext
                else:
                    print(f"Failed to read {seqfile}")
                    #input("Ctrl-C to abort or enter to continue")
                    break
                
            
        self.mml = mml
        self.variant = variant if variant and variant in get_variant_list(mml) else None
        self.id = basefile
        self.seqfile = seqfile
        self.spcfile = spcfile
        self.mmlremote = remote + basefile + ".mml" if remote else None
        
    def varid(self, token):
        return self.id + token + self.variant if self.variant else self.id
        
    def varseq(self, token):
        return self.seqfile + token + self.variant if self.variant else self.seqfile
        
    def process_spc(self, full_process):
        try:
            with open(spcfile, "rb") as f:
                spc = f.read()
        except IOError:
            print(f"Failed to read {spcfile}")
            input("Ctrl-C to abort or enter to continue")

        mml = self.mml
        # Handle SPC metadata
        title = re.search("(?<=#TITLE )([^;\n]*)", mml, re.IGNORECASE)
        album = re.search("(?<=#ALBUM )([^;\n]*)", mml, re.IGNORECASE)
        composer = re.search("(?<=#COMPOSER )([^;\n]*)", mml, re.IGNORECASE)
        arranged = re.search("(?<=#ARRANGED )([^;\n]*)", mml, re.IGNORECASE)
        self.title = title.group(0) if title else self.varid('_')
        self.album = album.group(0) if title else ""
        self.composer = composer.group(0) if composer else ""
        self.arranged = arranged.group(0) if arranged else ""
        spc = text_insert(spc, 0x2E, self.title, 0x20)
        spc = text_insert(spc, 0x4E, self.album, 0x20)
        spc = text_insert(spc, 0xB1, self.composer, 0x20)
        spc = text_insert(spc, 0x6E, self.arranged, 0x10)
        spc = byte_insert(spc, 0xAC, b"\x35\x30\x30\x30") # fade 5000
        spc = byte_insert(spc, 0xD2, b"\x30") # emulator unknown
        spc = byte_insert(spc, 0x23, b"\x1A") # header contains ID666 tag
        
        if full_process:
            self.duration = int(round(mfvi_trace(spc[0x1D00:0x4900])))
            spc = text_insert(spc, 0xA9, f"{self.duration:03}", 3)
        else:
            self.duration = int(spc[0xA9:0xAC].decode())
        if DURATION_INCLUDE_FADE:
            self.duration += 5
        self.duration_text = f"{int(self.duration // 60)}:{round(self.duration % 60):02}"
        
        try:
            with open(spcfile, "wb") as f:
                f.write(spc)
        except IOError:
            print(f"Failed to write {spcfile}")
            input("Ctrl-C to abort or enter to continue")
        
#def generate_temp_sample_list(full_sample_list, mml_file, outfile="sampleset.tmp", variant="_default_"):
def generate_temp_sample_list(full_sample_list, track, outfile="sampleset.tmp"):
    mml_file = track.seqfile
    variant = track.variant if track.variant else "_default_"
    
    with open(mml_file, "r") as f:
        mml = f.read()
    with open(full_sample_list, "r") as f:
        sampleset = f.readlines()
        
    inst_raw = mml_to_akao(mml, inst_only=True, variant=variant)
    sidstrings = []
    new_sampleset = ["[Samples]"]
    for i in range(16):
        sid = inst_raw[i*2]
        sidstrings.append(f"{sid:02X}")
    for line in sampleset:
        if line.upper().split(':')[0].strip() in sidstrings:
            new_sampleset.append(line)
    
    new_sampleset = "\n".join(new_sampleset)
    with open(outfile, "w") as f:
        f.write(new_sampleset)
    return outfile
        
# - Take a target name from input, we'll be working in that directory
# - (Do later) Allow specifying a single file instead of reprocessing all of them
# - Config file(s) for directory including page text, sample set, maybe variants to ignore
# - Create / clear target directory
# - Grab all mml files in source directory or from source playlist
# - (Do later) Check variants and expand tracklist to include variants
# - Insertmfvi the sample set into an intermediate ROM.
# - For each track (variant):
# - - Insertmfvi the track into a temp ROM. Use different freespace than samples did
# - - build_spc
# - - (Do later) Trace SPC to determine length
# - - Insert metadata into SPC
# - - (Do later) Write additional metadata to .info file (or to SPC at $FA00?)
# - - Put table column data in a sack to be opened later


# If a target page is specified at the command line, process that one. Otherwise,
# process all the pages defined in pages.cfg.
pages_cfg = configparser.ConfigParser()
pages_cfg.read("pages.cfg")

if len(sys.argv) >= 2:
    pages = [sys.argv[1].strip()]
else:
    pages = pages_cfg.sections()
    
if len(sys.argv) >= 3:
    update_filename = sys.argv[2].strip()
else:
    update_filename = None
    
for page in pages:
    if page not in pages_cfg:
        abort(f"Requested page {page} not present in pages.cfg.")
    cfg = pages_cfg[page]
    tracks = []
    
    if "remote" in cfg:
        remote = cfg["remote"].strip()
    else:
        remote = None
    outpath = cfg["outpath"].strip()
    mmlpath = cfg["mmlpath"].strip()
    brrpath = cfg["brrpath"].strip()
    seqlist = cfg["brrtable"].strip()
    variant = cfg["variant"].strip() if "variant" in cfg else None
    insertpath = os.path.join("mfvitools", "insertmfvi.py") + " "
    buildpath = os.path.join("mfvitools", "build_spc.py") + " "
    
    # TODO Create/clear target directory
    os.makedirs(outpath, exist_ok = True)
    
    # Make intermediate ROM with samples loaded
    # subprocess.run(insertpath + f"--list {cfg['brrtable'].strip()} --brrpath {cfg['brrpath'].strip()} --freespace 310000-5FFFFF --pad_samples --in {ROM} --out ~samples.smc", shell=True, input=b"\n")
    
    # Grab all mml files from source directory or source playlist(s)
    # Format for playlist config:
    # Separate playlist files with ';'
    # Separate playlist sections with ':'
    # Example: default.txt:victory:death;alternate.txt:victory:death
    seqfiles = {}
    if "playlist" in cfg:
        playlists = cfg["playlist"].split(';')
        print(f"{playlists=}")
        for playlist in playlists:
            pl = configparser.ConfigParser()
            sections = playlist.split(':')
            pfn = sections[0]
            sections = sections[1:]
            print(f"{pfn=}")
            pl.read(pfn)
            if not sections:
                sections = pl.sections()
            for section in sections:
                if section in pl:
                    ##seqfiles.extend([os.path.join(mmlpath, seq + ".mml") for seq in pl[section] if seq not in seqfiles])
                    for seq in pl[section]:
                        if seq not in seqfiles:
                            seqfiles[seq] = os.path.join(mmlpath, seq + ".mml")
    else:
        seqfileglob = glob(os.path.join(mmlpath, "*.mml"))
        for seqfile in seqfileglob:
            seq = os.path.splitext(os.path.basename(seqfile))[0]
            seqfiles[seq] = seqfile
        
    
    # TODO variant stuff
    # For variants we can make the file string "FILENAME?VARIANT"
    # to match insertmfvi inputs but maybe should keep them separate generally
    
    for key in sorted(seqfiles):
        seqfile = seqfiles[key]
        basefile = os.path.basename(os.path.splitext(seqfile)[0])
        spcfile = os.path.join(outpath, basefile + '.spc')
        
        track = Track(basefile, seqfile, spcfile, remote, variant)
        if track.mml is None:
            continue
            
        full_process = True
        if update_filename and basefile != update_filename:
            full_process = False
            
        if full_process:
            generate_temp_sample_list(seqlist, track)
            subprocess.run(insertpath + f"--list sampleset.tmp --mml {track.varseq('?')} 4C --brrpath {brrpath} --seqpath {mmlpath} --hack2 --freespace 310000-3FFFFF --metadata 300000 --in {ROM} --out ~temp.smc", shell=True, input=b"\n")
            subprocess.run(buildpath + f"~temp.smc 4C {spcfile}", shell=True)
    
        track.process_spc(full_process)
        tracks.append(track)
        
    # Build html for page
    # - nav
    nav = ""
    for navpage in pages_cfg.sections():
        nav_path = pages_cfg[navpage]['outpath']
        nav_pretty = nav_path.replace("_", " ").capitalize()
        if navpage != page:
            nav += f"<li><a href='../{nav_path}/' class='nav-inactive'>{nav_pretty}</a></li>"
        else:
            nav += f"<li><a href='../{nav_path}/' class='nav-active'>{nav_pretty}</a></li>"
    
    pagehead = head.replace("<!-- NAV -->", nav)
    # - main
    table = "<table>\n"
    table_columns = ["", "file", "Origin game", "Title", "Runtime", "Original composer", "Arranged/ported by", "Download"]
    table += table_row(table_columns, head=True)
    
    for track in tracks:
        play = f"<button type='button' onclick='playSpcFile(\"{track.varid(':')}\")'>PLAY</button>"
        dl = f"<a href='{os.path.basename(track.spcfile)}' id='{track.varid(':')}'>SPC</a>"
        if track.mmlremote:
            dl += f" <a href='{track.mmlremote}'>Source</a>"
        table += table_row([play, track.varid(':'), track.album, track.title, track.duration_text, track.composer, track.arranged, dl])
    table += "</table>\n"

    html = f"<head><title>{cfg['title']}</title></head>"
    html += pagehead
    html += f"<h1>{cfg['title']}</h1>"
    html += f"<p>{cfg['intro']}</p>"
    html += table
    html += foot
    
    with open(os.path.join(outpath, 'index.html'), "w") as f:
        f.write(html)
        
# Update main index
with open('indexhtml.template', "r") as f:
    index = f.read()

page_list = ""
for page in pages_cfg.sections():
    page_path = pages_cfg[page]['outpath']
    page_pretty = page_path.replace('_', ' ')
    page_list += f'<a href="{page_path}/">{page_pretty}</a><br>\n'

index = index.replace("<!-- LIBRARIES -->", page_list)
with open('index.html', "w") as f:
    f.write(index)