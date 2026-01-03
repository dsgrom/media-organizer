# ======= NEED TO FIGURE OUT EXIF FOR VIDEOS

# ====== bugs:
# currently if there are duplicates in import folder, does not copy some over because the import key is the same
    # if 2 DSCF0001.jpeg files in different folders, will not move both bc import key gets overwritten by second one
    # will create dups as DSCF0001_1.jpeg at destination though if i run program twice etc.
    # i think this isn't realy a huge problem. in the future when i drop files into import, it's unlikely to have dups?
# would be nice to cover this case though
# not a bug but imports in the future will go on my desktop so i can have a single import folder and empty it regularly


# future side project, add tags to photos by date range?

# dependencies
# exiftool - install instructions & downloaded links here: https://exiftool.org/install.html
    # - related homebrew link: https://formulae.brew.sh/formula/exiftool

# ================== helper functions for debugging/verifying what objects hold
# # get exif data of a single file
# with exiftool.ExifToolHelper() as et:
#     exif_data_single_file = et.get_metadata('/Users/kevin.huang/Downloads/b6a42f9f-095b-467d-8655-b8bcf4ae7988.JPG')
# for key, value in exif_data_single_file[0].items():
#     print(f"{key}: {value}")

# # exporting to JSON for easier reading, list of dicts
# with open("EXIF_checks.json", 'w') as json_file:
#     json.dump(dict_to_turn_into_json, json_file, indent=4) # Use indent for readability

# # exporting photo dest return check
# with open("photo_dest_return_check.json", 'w') as json_file:
#     json.dump(dict_to_turn_into_json, json_file, indent=4) # Use indent for readability


# ================== import packages
from pathlib import Path
import datetime
import exiftool
import json
import logging
logger = logging.getLogger(__name__)


# ================== other helper functions
# get the filename without ext - not really needed anymore, grabbing full filename with ext instead as key
# def get_true_stem(p):
#     p = Path(p)
#     while p.suffix:
#         p = Path(p.stem)
#     return str(p)

# if duplicate destination name (file already moved to dest folder), iterate unique name
def get_unique_path(p: Path) -> Path:
    """Appends an incremental number to a file path until a unique path is found."""
    if not p.exists():
        return p

    stem = p.stem
    suffix = p.suffix
    i = 1
    while True:
        new_name = f"{stem}_{i}{suffix}"
        new_path = p.with_name(new_name)
        if not new_path.exists():
            return new_path
        i += 1


# error logging
# ==================
# Configure logging to write to 'app.log' file
logging.basicConfig(
    filename='get_dest_paths.log',
    level=logging.DEBUG,  # Only log messages of level ERROR and higher
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'  # Append to the file (default mode)
)
# Create a logger instance
logger = logging.getLogger(__name__)
# ==================

# From import folder, grab list of filenames
# this list of filepaths will be passed to the EXIF data function to extract metadata and create the dest filepaths
# ================================================
def get_import_paths():  # return dictionary?
    """
    Get dictionaries of import files, to be organized.
        - format - {"filename.ext": "Path/to/filename.ext"}
        - returns 2 dictionaries, one for photo and one for video
    """
    # load JSON config file, read in config settings
    with open('config.json', encoding='utf-8') as f:
        categories = json.load(f)

    # grab import directory path, photo and video extensions from config
    imports_dir = Path(categories['import_directory'])
    photo_suffixes = set(categories['photo_extensions'])
    vid_suffixes = set(categories['video_extensions'])

    # # grab and sort paths for photo and video files
    # # photo extensions only
    # photo_files = {Path(p).name: p for p in imports_dir.rglob('*', case_sensitive=False) if p.suffix in photo_suffixes}  # noqa
    # # video extensions only
    # vid_files = {Path(v).name: v for v in imports_dir.rglob('*', case_sensitive=False) if v.suffix in vid_suffixes}

    # above dictionary comprehensions weren't working, so just using a normal for loop instead
    # grab and sort paths for photo and video files
    # photo extensions only
    photo_files = {}
    for p in imports_dir.rglob('*'):
        if p.suffix.upper() in photo_suffixes:
            photo_files[Path(p).name] = p
    # video extensions only
    vid_files = {}
    for v in imports_dir.rglob('*'):
        if v.suffix.upper() in vid_suffixes:
            vid_files[Path(v).name] = v

    # return tuple of photo and video import locations
    return {
        "photo_import_locations": photo_files,
        "vid_import_locations": vid_files
    }

# # testing - yay works
# a = get_import_paths()
# print(a['photo_import_locations'])
# print(a['vid_import_locations'])
# 
# len(a['photo_import_locations'])
# len(a['vid_import_locations'])
# 
# a['photo_import_locations']['Image17.jpg']


# get dictionaryies with photo name (without extension): location
# for example: "DSC_1111": PosixPath('originals/.../Nikon Z f')
# not splitting into RAW vs JPEG anymore, not helpful with editing workflow (i think?)
def get_dest_paths(photos, vids):
    '''
    Using EXIF data for each media file, build list of destination paths.
    '''
    # root paths for photo/vid destinations
    with open('config.json', encoding='utf-8') as f:
        categories = json.load(f)

    # grab import directory path, photo and video extensions from config
    photos_dest = Path(categories['photo_dest_directory'])
    vids_dest = Path(categories['vid_dest_directory'])

    # photos EXIF dict
    # the following returns a list of dictionaries
    # each element in the list is a dictionary that contains:
        # "SourceFile": "/Users/kevin.huang/Pictures/imports/202501 Japan trip/DSC_1212.NEF",
        # "EXIF:Model": "NIKON Z f",
        # "EXIF:CreateDate": "2025:01:13 20:04:39",
        # "File:FileType": "NEF"

    # PHOTOS - generate dictionary of {file_stem: destination_path} pairs
    with exiftool.ExifToolHelper() as et:
        photo_metadata_list = et.get_tags(photos.values(), tags=['EXIF:Model', 'EXIF:CreateDate', 'File:FileType'])

    photo_dest_pairs = {}  # initialize destination path dictionary

    for file in photo_metadata_list:
        try:
            file_date = datetime.datetime.strptime(file['EXIF:CreateDate'], "%Y:%m:%d %H:%M:%S")

            # try to create path from exif
            dir_path = Path(photos_dest, file_date.strftime("%Y") + "/" + file_date.strftime("%m") + "/" + file_date.strftime("%d") + "/" + file['EXIF:Model'].replace(" ", "_") + "/" + Path(file['SourceFile']).name)  # noqa

            photo_dest_pairs[Path(file['SourceFile']).name] = dir_path
        except KeyError:  # if exif category missing, skip
            logging.debug(f"KeyError bug: {file=}", exc_info=True)
            # print(f"Error: could not find some EXIF data for {file['SourceFile'].name}")
            print(f"Error (photo): KeyError - could not find some EXIF data for file {file['SourceFile']}")
        except ValueError:  # if exif data empty exist, skip
            logging.debug(f"ValueError bug: {file=}", exc_info=True)
            # print(f"Error: some blank EXIF data for {Path(file['SourceFile']).name}")
            print(f"Error (photo): ValueError - some blank EXIF data for {file['SourceFile']}")

    # videos EXIF dict
    # the following returns a list of dictionaries
    # each element in the list is a dictionary that contains:
        # "SourceFile": "/Users/kevin.huang/Pictures/imports/202501 Japan trip/DSC_1212.NEF",
        # ???

    # VIDEOS - generate dictionary of {file_stem: destination_path} pairs
    with exiftool.ExifToolHelper() as et:
        vid_metadata_list = et.get_tags(vids.values(), tags=['EXIF:Model', 'EXIF:CreateDate', 'File:FileType'])

    vid_dest_pairs = {}  # initialize destination path dictionary

    for file in vid_metadata_list:
        try:
            file_date = datetime.datetime.strptime(file['File:FileModifyDate'], "%Y:%m:%d %H:%M:%S")

            # try to create path from exif
            dir_path = Path(vids_dest, file_date.strftime("%Y") + "/" + file_date.strftime("%b") + "/" + file_date.strftime("%d") + "/" + file['EXIF:Model'].replace(" ", "_") + "/" + Path(file['SourceFile']).name)  # noqa

            vid_dest_pairs[Path(file['SourceFile']).name] = dir_path
        except KeyError:  # if exif category missing, skip
            logging.debug(f"KeyError bug: {file=}", exc_info=True)
            # print(f"Error: could not find some EXIF data for {file['SourceFile'].name}")
            print(f"Error (video): KeyError - could not find some EXIF data for file {file['SourceFile']}")
        except ValueError:  # if exif data empty exist, skip
            logging.debug(f"ValueError bug: {file=}", exc_info=True)
            # print(f"Error: some blank EXIF data for {Path(file['SourceFile']).name}")
            print(f"Error (video): ValueError - some blank EXIF data for {file['SourceFile']}")
    
    return {
        "photo_dest_locations": photo_dest_pairs,
        "vid_dest_locations": vid_dest_pairs
    }

# b = get_dest_paths(a['dest_dir'], a['photo_import_locations'], a['vid_import_locations'])
# 
# print(b)
# print(len(b))


def move_media(imports, dests):
    '''
    Moves files from import directory to destination directory, building directories as needed
    '''
    # error logging
    # =============
    # Configure logging to write to 'app.log' file
    logging.basicConfig(
        filename='move_media.log',
        level=logging.ERROR,  # Only log messages of level ERROR and higher
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a'  # Append to the file (default mode)
    )
    # Create a logger instance
    logger = logging.getLogger(__name__)
    # =============

    # for each filestem in dest (all keys in dest, for ex for photos: 'DSCF0474'):
        # move file from imports list location (value at key 'DSCF0474') to dests list location (value at 'DSCF0474')
    # PHOTOS
    for photo_key in dests['photo_dest_locations'].keys():
        # check if destination directory exists, if not create
        dests['photo_dest_locations'][photo_key].parent.mkdir(parents=True, exist_ok=True)

        # get unique dest path name
        try:
            unique_photo_target_path = get_unique_path(dests['photo_dest_locations'][photo_key])
            print(unique_photo_target_path)
        except KeyError:
            logging.debug(f"KeyError move_media", exc_info=True)
            # print(f"Error: could not find some EXIF data for {file['SourceFile'].name}")
            print(f"Error (move_media photos): KeyError - could not find key for {photo_key}")

        # move import file to destination file
        imports['photo_import_locations'][photo_key].rename(unique_photo_target_path)

    # vid files
    for vid_key in dests['vid_dest_locations'].keys():
        # check if destination directory exists, if not create
        dests['vid_dest_locations'][vid_key].parent.mkdir(parents=True, exist_ok=True)

        # get unique dest path name
        unique_vid_target_path = get_unique_path(dests['vid_dest_locations'][vid_key])

        # move import file to destination file
        imports['vid_import_locations'][vid_key].rename(unique_vid_target_path)

    print("Your media has been moved! If there are stragglers, they must be moved manually. Thank you!")


# TBD
# def move_sidecar():


# lines to actually run the code yay!
if __name__ == '__main__':
    import_paths = get_import_paths()
    dest_paths = get_dest_paths(import_paths['photo_import_locations'], import_paths['vid_import_locations'])
    move_media(import_paths, dest_paths)


# NX studio sidecar files need to be in the same directory as the image
# need to be in a subdir called 'NKSC_PARAM'
# these aren't really issues for future imports
# # but would like to move files that have already been edited in this initial import stage if it's not too hard

# photo RAW tags - these are the same for NEF, CR3, RAF, ORF RAWs (from my cameras at least. hopefully universal)
# 'EXIF:Make', 'EXIF:Model', 'EXIF:DateTimeOriginal', 'EXIF:CreateDate', 'File:FileType', 'File:FileTypeExtension'
# ================================================
