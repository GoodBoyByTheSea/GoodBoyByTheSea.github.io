import sqlite3
from pathlib import Path
import os
import shutil
from typing import Union
from functools import partial
import re
import pandas as pd
import logging

logger = logging.getLogger()
logger.setLevel('DEBUG')
logger.addHandler(logging.StreamHandler())

new_downloads = r'D:\Personal\Porn\ToFile'
path_complete = r'D:\Personal\Porn\Movies'
# new_downloads = r'C:\Personal\Porn\ToFile'
# path_complete = r'C:\Personal\Porn\Movies'

onlyfans_path = r"D:\Personal\Porn\Movies\OnlyFans"
STASH_DB = r"E:\Stash\stash-go.sqlite"
# onlyfans_path = r"C:\Personal\Porn\Movies\OnlyFans"
# STASH_DB = r"C:\Personal\Porn\Stash\stash-go.sqlite"


def rename_files(path: Union[str, Path],
                 add_to_front='',
                 remove_from_name: Union[str, list] = '',
                 replace: Union[dict, None] = None,
                 debug=False) -> None:
    if type(path) == str:
        path = Path(path)
    files = os.listdir(path)

    for root, dirs, files in os.walk(path):
        # Get subdirectory name
        subdirectory_name = os.path.basename(root)
        for filename in files:
            old_path = os.path.join(root, filename)
            new_filename = filename

            if remove_from_name:
                if type(remove_from_name) == str:
                    remove_from_name = [remove_from_name]
                for i in remove_from_name:
                    new_filename = new_filename.replace(i, '')

            if replace is not None:
                for new, old in replace.items():
                    if type(old) == str:
                        old = [old]
                    for o in old:
                        new_filename = new_filename.replace(o, new)

            new_filename = f'{add_to_front}{new_filename}'
            new_path = os.path.join(root, new_filename)

            if debug:
                if new_filename != filename:
                    logger.debug(f'File {filename} renamed to {new_filename}')
            else:
                if new_filename != filename:
                    os.rename(old_path, new_path)
                    logger.debug(f'File {filename} renamed to {new_filename}')


def modify_file_names(base_dir, func, debug=True):
    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            new_filename = func(filename)
            if new_filename != filename:
                old_path = os.path.join(root, filename)
                new_filename = func(filename)
                new_path = os.path.join(root, new_filename)
                if debug:
                    logger.debug(f"(debug) Renamed: {old_path} -> {new_path}")
                else:
                    os.rename(old_path, new_path)
                    logger.debug(f"Renamed: {old_path} -> {new_path}")


def file_movies(new_files_dir, dest_dir, debug=True):
    # new_files = os.listdir(new_files_dir)
    results = set()
    for root, dirs, files in os.walk(new_files_dir):
        for filename in files:
            try:
                m = re.match(r'(?P<studio>.*?) - ', filename)
                studio = m.groupdict()['studio']
                if os.path.exists(os.path.join(dest_dir, studio)):
                    new_filename = filename.replace(f'{studio} - ', "", 1)
                    new_path = os.path.join(dest_dir, studio, new_filename)
                    old_path = os.path.join(root, filename)
                    if debug:
                        logger.debug(f"(debug) Renamed: {old_path} -> {new_path}")
                    else:
                        os.rename(old_path, new_path)
                        logger.debug(f"Renamed: {old_path} -> {new_path}")
                else:
                    # logger.debug(f'No folder setup for {studio}')
                    results.add(f'No folder setup for {studio}')
            except AttributeError as e:
                logger.debug(f'File {filename} does not include studio name')
            except Exception as e:
                results.add(f'Error while renaming {filename}')
    for r in results:
        logger.debug(r)
    return results


def fix_movie_title(file_name):
    def remove_resolution(text):
        r = ' ?[\(|\[][0-9]{3,4}[p|P][\)\]]'
        text = re.sub(r, '', text)
        for i in [' (FHD)', ' FHD1080', ' 1080p', ' 2160p', ' 4K']:
            text = text.replace(i, '')
        return text

    file_name = file_name.replace('–', '-')
    file_name = file_name.replace('[', '')
    file_name = file_name.replace(']', '')
    file_name = file_name.replace('@', '')
    file_name = remove_resolution(file_name)
    return file_name


def remove_folder_name_from_file_name(base_dir, use_exclude_list=True, debug=True):
    exclude = [
        'OnlyFans',
        'Misc']
    """
    Iterates through subdirectories in 'base_dir' and renames files containing the subdirectory name.
    Args:
    base_dir: The base directory to start iterating from.
    """
    for root, dirs, files in os.walk(base_dir):
        # Get subdirectory name
        subdirectory_name = os.path.basename(root)
        for filename in files:
            # Check if filename contains subdirectory name (case-insensitive)
            debug_msg = ''
            skip = False
            if subdirectory_name.lower() in filename.lower():
                new_filename = filename.replace(f'{subdirectory_name} - ', "", 1)
                new_filename = new_filename.replace(subdirectory_name, "", 1)  # Replace only first occurrence
                new_path = os.path.join(root, new_filename)
                old_path = os.path.join(root, filename)
                if use_exclude_list:
                    skip = False
                    for i in exclude:
                        if i in root:
                            skip = True
                            debug_msg = f"Folder name not removed for {i} file: {filename}"

                if debug and not debug_msg:
                    debug_msg = f"(debug) Folder name removed from: {filename} -> {new_path}"
                else:
                    if not skip:
                        os.rename(old_path, new_path)
                        debug_msg = f"Folder name removed from: {filename} -> {new_path}"
                print(debug_msg)


def reconcile_studios(path):
    studio_folders = os.listdir(path)
    with sqlite3.connect(STASH_DB) as conn:
        db_studios = conn.execute("SELECT name from studios")
        db_studios = db_studios.fetchall()
        db_studios = [i[0] for i in db_studios]
        result = {'Missing Folder': [s for s in db_studios if s not in studio_folders],
              'Missing Studio': [s for s in studio_folders if s not in db_studios]}

    return result


def is_scene_organized(scene_id):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT organized from scenes where id = ?", (scene_id,))
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def is_image_organized(image_id):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT organized from images where id = ?", (image_id,))
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def set_scene_organized(scene_id, organized=True):
    with sqlite3.connect(STASH_DB) as conn:
        conn.execute("UPDATE scenes SET organized = ? where id = ?", (organized, scene_id))
        conn.commit()
        return is_scene_organized(scene_id)


def set_image_organized(image_id, organized=True):
    with sqlite3.connect(STASH_DB) as conn:
        conn.execute("UPDATE images SET organized = ? where id = ?", (organized, image_id))
        conn.commit()
        return is_image_organized(image_id)


def get_image_id_from_filename(filename):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT id from files where basename like ?", (f'%{filename}%',))
        file_id = cur.fetchone()
        if file_id is not None:
            file_id = file_id[0]
            scene_id = get_image_id_from_file_id(file_id)
            return scene_id
        else:
            logger.debug(f"No file in Stash found for {filename}")


def get_image_id_from_file_id(file_id):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT image_id from images_files where file_id = ?", (file_id,))
        image_id = cur.fetchone()
        if image_id is not None:
            image_id = image_id[0]
            return image_id
        else:
            logger.debug(f"No image_id in Stash found for {file_id}")


def get_scene_id_from_filename(filename):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT id from files where basename like ?", (f'%{filename}%',))
        file_id = cur.fetchone()
        if file_id is not None:
            file_id = file_id[0]
            scene_id = get_scene_id_from_file_id(file_id)
            return scene_id
        else:
            logger.debug(f"No file in Stash found for {filename}")


def get_scene_id_from_file_id(file_id):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT scene_id from scenes_files where file_id = ?", (file_id,))
        scene_id = cur.fetchone()
        if scene_id is not None:
            scene_id = scene_id[0]
            return scene_id
        else:
            logger.debug(f"No scene_id in Stash found for {file_id}")


def get_file_id_from_scene_id(scene_id):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT file_id from scenes_files where scene_id = ?", (scene_id,))
        scene_id = cur.fetchone()
        if scene_id is not None:
            scene_id = scene_id[0]
            return scene_id
        else:
            print(f"No file_id in Stash found for {scene_id}")


def get_studio_id_from_name(studio_name):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT id from studios where name = ?", (studio_name,))
        studio_id = cur.fetchone()[0]
        return studio_id


def get_studio_from_scene_id(scene_id):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT studio_id from scenes where id = ?", (scene_id,))
        studio_id = cur.fetchone()[0]
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT name from studios where id = ?", (studio_id,))
        studio = cur.fetchone()
        if studio is not None:
            studio = studio[0]
            return studio
        else:
            print(f"No file_id in Stash found for {scene_id}")


def get_studio_from_image_id(image_id):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT studio_id from images where id = ?", (image_id,))
        studio_id = cur.fetchone()[0]
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT name from studios where id = ?", (studio_id,))
        studio = cur.fetchone()
        if studio is not None:
            studio = studio[0]
            return studio
        else:
            print(f"No file_id in Stash found for {image_id}")

def get_scene_id_from_hash(hash):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT file_id from files_fingerprints where fingerprint = ?", (hash,))
        file_id = cur.fetchone()
        if file_id is not None:
            file_id = file_id[0]
            scene_id = get_scene_id_from_file_id(file_id)
            return scene_id
        else:
            print(f"No file in Stash found for {file_id}")


def set_scene_description(scene_id, details=None, date=None, title=None, overwrite=False, debug=True, *args, **kwargs):
    if is_scene_organized(scene_id):
        if not overwrite:
            logger.debug(f'Scene {scene_id} already organized')
            return
        logger.warning(f'Scene {scene_id} already organized, updating anyway')

    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT details, date, title from scenes WHERE scenes.id = ?", (scene_id,))
        row = cur.fetchone()
        if row is None:
            logger.debug(f"No scene found for scene_id {scene_id}")
            return False
        current_details, current_date, current_title = row
        if current_details != details or overwrite:
            conn.execute("UPDATE scenes SET details = ? WHERE scenes.id = ?", (details, scene_id))
            conn.commit()
            logger.debug(f'Details for scene {scene_id} updated to {details}')
        else:
            logger.debug(f'Details for scene {scene_id} already set')

        if current_date != date or overwrite:
            conn.execute("UPDATE scenes SET date = ? WHERE scenes.id = ?", (date, scene_id))
            conn.commit()
            logger.debug(f'Date for scene {scene_id} updated to {date}')
        else:
            logger.debug(f'Date for scene {scene_id} already set')
        if current_title != title or overwrite:
            conn.execute("UPDATE scenes SET title = ? WHERE scenes.id = ?", (title, scene_id))
            conn.commit()
            logger.debug(f'Title for scene {scene_id} updated to {title}')
        else:
            logger.debug(f'Title for scene {scene_id} already set')


def set_image_description(image_id, details=None, date=None, title=None, overwrite=False, debug=True, *args, **kwargs):
    if is_image_organized(image_id):
        if not overwrite:
            logger.debug(f'Image {image_id} already organized')
            return
        logger.warning(f'Image {image_id} already organized, updating anyway')

    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT details, date, title from images WHERE images.id = ?", (image_id,))
        row = cur.fetchone()
        if row is None:
            logger.debug(f"No image found for scene_id {image_id}")
            return False
        current_details, current_date, current_title = row
        if current_details != details or overwrite:
            conn.execute("UPDATE images SET details = ? WHERE images.id = ?", (details, image_id))
            conn.commit()
            logger.debug(f'Details for image {image_id} updated to {details}')
        else:
            logger.debug(f'Details for image {image_id} already set')

        if current_date != date or overwrite:
            conn.execute("UPDATE images SET date = ? WHERE images.id = ?", (date, image_id))
            conn.commit()
            logger.debug(f'Date for image {image_id} updated to {date}')
        else:
            logger.debug(f'Date for image {image_id} already set')
        if current_title != title or overwrite:
            conn.execute("UPDATE images SET title = ? WHERE images.id = ?", (title, image_id))
            conn.commit()
            logger.debug(f'Title for image {image_id} updated to {title}')
        else:
            logger.debug(f'Title for image {image_id} already set')


def get_all_scene_ids_from_studio_name(studio_name):
    studio_id = get_studio_id_from_name(studio_name)
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT id from scenes where studio_id = ?", (studio_id,))
        scene_ids = cur.fetchall()
        return [i[0] for i in scene_ids]


def set_scene_url(scene_id, url, debug=False, *args, **kwargs):
    with sqlite3.connect(STASH_DB) as conn:
        # Check if the url is there already
        cur = conn.execute("SELECT position from scene_urls where scene_id = ? and url = ? order by position desc",
                           (scene_id, url))
        exists = cur.fetchone()
        if exists:
            return
        cur = conn.execute("SELECT position from scene_urls where scene_id = ? order by position desc", (scene_id,))
        position = cur.fetchone()
        if position is None:
            position = 0
        else:
            position = position[0] + 1
        if debug:
            logger.debug(f'(debug) URL for scene {scene_id} added to position {position}: {url}')
        else:
            conn.execute("INSERT INTO scene_urls VALUES (?, ?, ?)", (scene_id, position, url))
            conn.commit()
            logger.debug(f'URL for scene {scene_id} added to position {position}: {url}')


def update_ofuser_scenes(ofuser):
    of_db = os.path.join(onlyfans_path, ofuser, "Metadata", "user_data.db")
    if not os.path.exists(of_db):
        logger.debug(f"No folder found for of-user: {ofuser}")
        return False
    with sqlite3.connect(of_db) as conn:
        cur = conn.execute("SELECT post_id, text, created_at from posts")
        posts = cur.fetchall()
        # posts = {i[0]: i[1] for i in posts}
    for post_id, details, created_at in posts:
        scene_id = get_scene_id_from_filename(post_id)
        if scene_id is None:
            print(f'No scene_id found for post_id {post_id}: {details}')
            image_id = get_image_id_from_filename(post_id)
            if image_id is None:
                continue
            if is_image_organized(image_id):
                print(f'image_id {image_id} already organized')
                continue
            studio = get_studio_from_image_id(image_id)
            title = f'{studio}: {created_at[0:10]} ({post_id})'
            set_image_description(image_id=image_id, details=details, date=created_at, title=title)
            set_image_organized(image_id=image_id)
            continue
        elif is_scene_organized(scene_id):
            print(f'scene_id {scene_id} already organized')
            continue
        studio = get_studio_from_scene_id(scene_id)
        title = f'{studio}: {created_at[0:10]} ({post_id})'
        set_scene_description(scene_id=scene_id, details=details, date=created_at, title=title)
        set_scene_organized(scene_id=scene_id)


def update_onlyfans():
    of_users = os.listdir(onlyfans_path)
    for ofuser in of_users:
        update_ofuser_scenes(ofuser)


def update_scene_by_hash(hash, details=None, date=None, title=None, url=None, *args, **kwargs):
    scene_id = get_scene_id_from_hash(hash)
    set_scene_description(scene_id=scene_id, details=details, date=date, title=title)
    if url:
        set_scene_url(scene_id=scene_id, url=url)


def read_csv(path):
    path = r'D:\Personal\Porn\data.csv'
    df = pd.read_csv(path)
    data = df.to_dict(orient='records')
    for row in data:
        if row['scene_id'] is not None:
            set_scene_description(**row)
        if 'url' in row:
            set_scene_url(scene_id=row['scene_id'], url=row['url'])


def update_from_csv():
    path = r'C:\Personal\Porn\tim.csv'
    df = pd.read_csv(path)
    data = df.to_dict(orient='records')
    for row in data:
        hash = row['fingerprint']
        update_scene_by_hash(hash, **row)


file_name_replacements = {
    'Dark Alley Media -': ['Dark Alley -', 'Darkalley -'],
    'DrCumControl': ['Dr Cum Control'],
    'Dream Boy Bondage': ['DreamBoyBondage'],
    'Eric Videos': ['EricVideos'],
    'GuyBone': ['Guy Bone'],
    'Hard Kinks': ['HardKinks'],
    'Hairy and Raw': ['Hairy Aand Raw'],
    'Himeros.TV': ['Himeros TV', 'HimerosTV'],
    'Kink Men': ['KinkMen'],
    'TIM Suck': ['Tim Suck', 'TimSuck', 'TIMSuck'],
    'TIM Fuck': ['Tim Fuck', 'TimFuck', 'TIMFuck'],
    'TIM Jack': ['Tim Jack', 'TimJack', 'TIMJack'],
}


def set_scene_title(scene_id, title, debug=True):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT details from scenes WHERE scenes.id = ?", (scene_id,))
        current_title = cur.fetchone()
        if current_title is None:
            pass
        else:

            current_title = current_title[0]
            if debug:
                print(f'(debug) Title for scene {scene_id} updated to {title}')
            else:
                if current_title != title:
                    conn.execute("UPDATE scenes SET title = ? WHERE scenes.id = ?", (title, scene_id))
                    conn.commit()
                    print(f'Title for scene {scene_id} updated to {title}')
                else:
                    print(f'Title for scene {scene_id} already set')
                    pass


def set_scene_details(scene_id, debug=True):
    with sqlite3.connect(STASH_DB) as conn:
        file_id = get_file_id_from_scene_id(scene_id)
        cur = conn.execute("SELECT basename from files WHERE id = ?", (file_id,))
        file_name = cur.fetchone()
        if file_name is None:
            print(f'file_name not found for scene_id {scene_id}')
            return
        else:
            file_name = file_name[0]
        cur = conn.execute("SELECT title, details, studio_id from scenes WHERE id = ?", (scene_id,))
        current_title, current_description, studio_id = cur.fetchone()
        cur = conn.execute("SELECT name from studios WHERE id = ?", (studio_id,))
        studio_name = cur.fetchone()
        if studio_name is None:
            print(f'No studio set for scene_id {scene_id}: {file_name}')
            return
        else:
            studio_name = studio_name[0]
        file_name = file_name.split('.')
        file_name = '.'.join(file_name[:-1])
        title = f'{file_name}'
        description = f'{studio_name} - {file_name}'
        if current_description is None:
            if debug:
                print(f'(debug) Scene description set for {file_name}: {description}')
            else:
                set_scene_description(scene_id=scene_id, description=description, debug=debug)
                print(f'Scene description set for {file_name}: {description}')
        else:
            if current_description != description:
                print(f'Scene description set for {file_name} does not match: {description}')
        if current_title is None:
            if debug:
                print(f'(debug) Scene title set for {file_name}: {title}')
            else:
                set_scene_title(scene_id=scene_id, title=title, debug=debug)
                print(f'Scene title set for {file_name}: {title}')
        else:
            if current_title != title:
                print(f'Scene title for {file_name} is {current_title} does not match: {title}')


def update_all_scene_details(debug=True):
    with sqlite3.connect(STASH_DB) as conn:
        cur = conn.execute("SELECT id from scenes")
        scene_ids = cur.fetchall()
        scene_ids = [s[0] for s in scene_ids]
    for scene_id in scene_ids:
        set_scene_details(scene_id=scene_id, debug=debug)


if __name__ == '__main__':
    debug = False

    rec = reconcile_studios(path_complete)
    [logger.debug(f'{i},') for i in rec['Missing Studio']]
    ################################################
    # Step One #
    # Fix file names for new downloads
    # Like "Studio - filename.ext"
    ################################################
    add_to_front = ''
    remove_from_name = ['']
    replace = {'Kink Men': ['KinkMen'],
               }
    rename_files(new_downloads,
                 add_to_front=add_to_front,
                 remove_from_name=remove_from_name,
                 replace=replace,
                 debug=debug)

    #################################################
    # Step Two #
    # Fix file names
    #################################################
    # Subs common changes like EricVideos --> Eric Videos
    rename_files(new_downloads, replace=file_name_replacements, debug=debug)
    # rename_files(path_complete, replace=file_name_replacements, debug=debug)

    # Fix the file names, remove 1080p, etc.
    modify_file_names(new_downloads, fix_movie_title, debug=debug)
    # modify_file_names(path_complete, fix_movie_title, debug=debug)

    #################################################
    # Step Three #
    # File new videos into studio specific folders
    # Like "Studio - filename.ext"
    #################################################
    file_movies(new_downloads, path_complete, debug=debug)

    # update_all_scene_details()

    #################################################
    # Cleanup #
    # For existing filed movies
    #################################################
    # Remove studios from file names if it matches the folder
    # remove_folder_name_from_file_name(path_complete)

    # Fix Folders:
    # D:\Personal\Porn\Movies\New\Sam Bridle Pack
    # D:\Personal\Porn\Movies\Complete\Misc
    # D:\Personal\Porn\Movies
    # Add 'New' tag

    # Remove studios from file names if it matches the folder
    # remove_folder_name_from_file_name(path)


of_auth = {
  "USER_ID": "16597096",
  "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
  "X_BC": "7f2f11520436474aba6a539b96b5815e3c2446b4",
  "COOKIE": "auth_id=16597096; sess=ovdeejf2po8vjb78p9lvmoekq8;"
}