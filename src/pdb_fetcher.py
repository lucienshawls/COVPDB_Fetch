import requests
from bs4 import BeautifulSoup as bs
import os
import json

DOMAIN = 'https://drug-discovery.vm.uni-freiburg.de'
MAIN_PAGE = 'https://drug-discovery.vm.uni-freiburg.de/covpdb/proteins_list/initial=Allsortedby=protein_name'

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Referer': 'https://drug-discovery.vm.uni-freiburg.de/covpdb/download',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.46',
    'sec-ch-ua': '"Chromium";v="118", "Microsoft Edge";v="118", "Not=A?Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
}

requests.packages.urllib3.disable_warnings()

def get_ligand_info(url, page=1):
    ligand_info_list_cur_page = []
    resp = requests.get(f"{url}?page={str(page)}", headers=HEADERS, verify=False)
    resp.encoding='utf-8'
    html_doc = resp.text
    soup = bs(html_doc, 'html.parser')
    
    result_table = soup.find(class_='result_table')
    rows = result_table.find('tbody').find_all('tr')
    for row in rows:
        ligand_info = {}
        columns = row.find_all('td')
        ligand_info['id'] = columns[0].get_text().strip()

        print(f"\tligand id={ligand_info['id']}")

        ligand_info['structure_img_url'] = f"{DOMAIN}{columns[7].find('img').get('src').strip()}"
        ligand_info_list_cur_page.append(ligand_info)
    return ligand_info_list_cur_page

def get_ligand_database(url):
    resp = requests.get(url, headers=HEADERS, verify=False)
    resp.encoding='utf-8'
    html_doc = resp.text
    soup = bs(html_doc, 'html.parser')
    pagination = soup.find(class_='pagination')
    a_tag_list = pagination.find_all('a')
    max_page = int(a_tag_list[-1].get_text())

    ligand_info_list = []
    for i in range(1, max_page + 1):
        ligand_info_list_cur_page = get_ligand_info(url=url, page=i)
        ligand_info_list += ligand_info_list_cur_page
    return ligand_info_list

def get_pdb_info(page=1):

    print(f"pdb page={str(page)}")

    pdb_info_list_cur_page = []
    url = f"{MAIN_PAGE}?page={str(page)}"
    resp = requests.get(url, headers=HEADERS, verify=False)
    resp.encoding='utf-8'
    html_doc = resp.text
    soup = bs(html_doc, 'html.parser')
    result_table = soup.find(class_='result_table')
    rows = result_table.find('tbody').find_all('tr')
    for row in rows:
        pdb_info = {}
        columns = row.find_all('td')
        pdb_info['id'] = columns[0].get_text().strip()

        print(f"pdb id={pdb_info['id']}")

        pdb_info['name'] = columns[1].find('a').get_text().strip()
        pdb_info['ligands'] = {
            'info_url': f"{DOMAIN}{columns[4].find('a').get('href')}"
        }
        pdb_info_list_cur_page.append(pdb_info)
    return pdb_info_list_cur_page

def get_pdb_database(json_file_name=''):
    if json_file_name != '':
        with open(json_file_name, 'r', encoding='utf-8') as f:
            json_text = f.read()
        return json.loads(json_text)['pdb_data']
    resp = requests.get(MAIN_PAGE, headers=HEADERS, verify=False)
    resp.encoding='utf-8'
    html_doc = resp.text
    soup = bs(html_doc, 'html.parser')
    pagination = soup.find(class_='pagination')
    a_tag_list = pagination.find_all('a')
    max_page = int(a_tag_list[-1].get_text())

    pdb_info_list = []
    for i in range(1, max_page + 1):
        pdb_info_list_cur_page = get_pdb_info(page=i)
        pdb_info_list += pdb_info_list_cur_page
    for i in range(len(pdb_info_list)):
        ligand_info_url = pdb_info_list[i]['ligands']['info_url']

        print(f"getting ligands for pdb id={pdb_info_list[i]['id']}")

        pdb_info_list[i]['ligands']['structures'] = get_ligand_database(ligand_info_url)
    return pdb_info_list

def standardize_name(file_name):
    file_name_standardized = file_name
    invalid_chars = ['"', '*', '<', '>', '?', '\\', '/', '|', ':']
    for char in invalid_chars:
        if char in file_name:
            file_name_standardized = file_name_standardized.replace(char, ' ')
    return file_name_standardized

def download(url, path):
    resp = requests.get(url=url, headers=HEADERS, verify=False)
    with open(path, 'wb') as f:
        f.write(resp.content)

def organize_files(database, root_path='pdb_database_svg'):
    os.makedirs(root_path, exist_ok=True)
    for pdb in database:
        pdb_id = pdb['id']

        print(f"pdb id={pdb_id}")

        pdb_name = standardize_name(pdb['name'])
        for ligand in pdb['ligands']['structures']:
            ligand_id = ligand['id']

            print(f"\tligand id={ligand_id}")

            ligand_structure_img_url = ligand['structure_img_url']
            img_file_name = f"[pdb-{pdb_id}]-[ligand-{ligand_id}]-[{pdb_name}].svg"
            download(url=ligand_structure_img_url, path = f"{root_path}/{img_file_name}")

def transform_format(database, root_path_svg='pdb_database_svg', root_path='pdb_database'):
    import cairosvg
    os.makedirs(root_path, exist_ok=True)
    for pdb in database:
        pdb_id = pdb['id']

        print(f"pdb id={pdb_id}")

        pdb_name = standardize_name(pdb['name'])
        for ligand in pdb['ligands']['structures']:
            ligand_id = ligand['id']

            print(f"\tligand id={ligand_id}")

            img_file_name = f"[pdb-{pdb_id}]-[ligand-{ligand_id}]-[{pdb_name}]"
            cairosvg.svg2png(url=f"{root_path_svg}/{img_file_name}.svg", write_to=f"{root_path}/{img_file_name}.png")

def main():
    database = get_pdb_database()
    # database = get_pdb_database(json_file_name='pdb_database.json')
    json_text = json.dumps({'pdb_data': database})
    with open('pdb_database.json', 'w', encoding='utf-8') as f:
        f.write(json_text)
    organize_files(database=database)
    transform_format(database=database)

if __name__ == "__main__":
    main()
    pass
