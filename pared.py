# SPDX-License-Identifier: GPL-2.0-or-later

import requests
from typing import NamedTuple, Dict, List, Union
import json
from datetime import datetime, timedelta
import time
import sys
import os

API_TOKEN=os.environ.get("PW_API_KEY")
PATCHWORK_INSTANCE = os.environ.get("PW_API_URL", "https://patchwork.ozlabs.org/api/1.2/")
PROJECT = os.environ.get("PW_PROJECT", 'patchwork')
PER_PAGE = 100 # balance between not too many requests and not too big.
MAX_FETCH_AGE_DAYS = int(os.environ.get("PW_FETCH_DAYS", "180")) # only download N days worth of patches
MAX_PATCH_AGE_DAYS = 180 # only consider patches sent in the last N days
# if MAX_PATCH_AGE_DAYS > MAX_FETCH_AGE_DAYS, we will accumulate up to
# MAX_PATCH_AGE_DAYS of data before starting to throw out data. This can
# be handy to avoid overstressing the server... not that fetching pages of
# patches is all that onerous.
PARED_DATASTORE = os.environ.get("PARED_DATASTORE", "subjects.json")

class PatchNameOccurrence(NamedTuple):
    id: int
    date: str

def strip_name(name: str) -> str:
    if name[0] != '[':
        return name

    try:
        end = name.index(']')
        return name[(end+1):].strip()
    except ValueError:
        return name

from requests.structures import CaseInsensitiveDict

def relate(id1, id2):
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    headers["Authorization"] = f"Token {API_TOKEN}"
    content = f'{{"related": [{id2}]}}'
    r = requests.patch(PATCHWORK_INSTANCE + 'patches/' + str(id1) + '/',
        data=content,
        headers=headers)
    
    print("relate", id1, id2, '=>', r.status_code, r.raw.data)

def generate_subject_map() -> Dict[str, List[PatchNameOccurrence]]:
    oldest_date = datetime.now() - timedelta(days=MAX_FETCH_AGE_DAYS)
    url = PATCHWORK_INSTANCE + 'patches/?project=' + PROJECT + '&since=' + oldest_date.isoformat() + '&per_page=' + str(PER_PAGE)
    return update_subject_map(url, {})

def update_subject_map(base_url: str, in_map: Dict[str, List[PatchNameOccurrence]]) -> Dict[str, List[PatchNameOccurrence]]:
    subject_map = in_map

    page = 1

    while True:
        print("Fetching page", page)
        patches = requests.get(base_url + '&page=' + str(page))

        if patches.status_code != 200:
            print("Patches not fetched successfully")
            print(patches.status_code)
            print(patches.headers)
            sys.exit(1)

        for p in patches.json():
            pno = [PatchNameOccurrence(id=p['id'], date=p['date'])]

            name = strip_name(p['name'])
            if name in subject_map:
                # `since` is not exclusive of the max date so we see the
                # most recent patch over and over
                if p['id'] not in [e.id for e in subject_map[name]]:
                    relate(subject_map[name][0].id, pno[0].id)
                    subject_map[name] += pno
            else:
                subject_map[name] = pno

        if 'Link' in patches.headers and 'rel="next"' in patches.headers['Link']:
            pass
        else:
            break

        page += 1

    return subject_map

def json_to_pnos(in_json: Dict[str, List[Union[int, str]]]) -> Dict[str, List[PatchNameOccurrence]]:
    out_map = {}
    for name in in_json:
        out_list = [PatchNameOccurrence(entry[0], entry[1]) for entry in in_json[name]]
        out_map[name] = out_list
    return out_map

def expire_subject_map(in_map: Dict[str, List[PatchNameOccurrence]]) -> Dict[str, List[PatchNameOccurrence]]:
    oldest_date = datetime.now() - timedelta(days=MAX_PATCH_AGE_DAYS)
    
    new_map = {}

    for name in in_map:
        new_list = []
        for pno in in_map[name]:
            entry_date = datetime.fromisoformat(pno.date)
            if entry_date > oldest_date:
                new_list += [pno]
            else:
                print("Expiring", pno, "for", name)

            if new_list:
                new_map[name] = new_list
            else:
                print("Expiring all of", name)

    return in_map


if __name__ == '__main__':
    try:
        with open(PARED_DATASTORE, 'r') as f:
            subject_map = json_to_pnos(json.load(f))
    except Exception as e:
        print(e)
        subject_map = generate_subject_map()
        with open(PARED_DATASTORE, 'w') as f:
            json.dump(subject_map, f)

    subject_map = expire_subject_map(subject_map)
    max_patch_id = 0
    max_date = '2021-08-01T00:00:00'
    for es in subject_map.values():
        max_patch_id = max([max_patch_id] + [e.id for e in es])
        max_date = max([max_date] + [e.date for e in es])

    print(max_date, max_patch_id)

    while True:
        print(datetime.now().isoformat(), "- waking")
        url = PATCHWORK_INSTANCE + 'patches/?project=' + PROJECT + '&since=' + max_date + '&per_page=' + str(PER_PAGE)
        subject_map = update_subject_map(url, subject_map)
        subject_map = expire_subject_map(subject_map)

        with open(PARED_DATASTORE, 'w') as f:
            json.dump(subject_map, f)

        for es in subject_map.values():
            max_patch_id = max([max_patch_id] + [e.id for e in es])
            max_date = max([max_date] + [e.date for e in es])
        print(max_date, max_patch_id)

        print(datetime.now().isoformat(), "- sleeping")
        time.sleep(300)
