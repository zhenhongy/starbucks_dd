import requests
from bs4 import BeautifulSoup as Soup
import pandas as pd
import json
import settings

zip_code = pd.read_table('./data/zip_boston_neighborhood.txt', header=0, names = ['zip_code','region'], dtype = 'object')

def store_dict(source, id, coordinates, zip_code, output):
     out = output
     
     for store in source:
         if store[id] in output.keys():
             continue
         else:
             out[store[id]] = {'zip_code': zip_code, 'geo': store[coordinates]}
             
     return out          

#starbucks
sb_store = {}
for z in zip_code.zip_code.values:
    url = "https://www.starbucks.com/store-locator?place={}".format(z)
    page = requests.get(url)
    soup = Soup(page.content, 'html.parser')
    store = soup.find_all('div',id = 'bootstrapData')
    store = store[0]
    store = store.get_text()
    sb_dict = json.loads(store)
    sb_dict = sb_dict['storeLocator']['locationState']['locations']
    sb_store = store_dict(sb_dict, 'id', 'coordinates', z, sb_store)

#dd
dd_store = {}
dd_dict = []
for z in zip_code.zip_code.values:
    url = "https://www.mapquestapi.com/search/v2/radius?callback=json111206657990027752725_1504756855257&key=Gmjtd%7Clu6t2luan5%252C72%253Do5-larsq&origin={}&units=m&maxMatches=30&radius=25&hostedData=mqap.33454_DunkinDonuts&ambiguities=ignore&_=1504756855258".format(z)
    page = requests.get(url)
    soup = Soup(page.content,'html.parser')
    store = soup.get_text()
    store = store[store.find("(")+1:store.rfind(")")]
    dd_dict_temp = json.loads(store)
    dd_dict_temp = dd_dict_temp['searchResults']
    for dd in dd_dict_temp:
        dd_dict.append(dd['fields'])
    dd_store = store_dict(dd_dict, 'recordid', 'mqap_geography', z, dd_store)
    
sb_nearby = pd.DataFrame([{'id': key, 'lat': sb_store[key]['geo']['latitude'], 'lon': sb_store[key]['geo']['longitude']}, 'zip_code': sb_store[key]['zip_code'] for key in sb_store.keys()])
dd_nearby = pd.DataFrame([{'id': key, 'lat': dd_store[key]['geo']['latLng']['lat'],'lon': dd_store[key]['geo']['latLng']['lng']}, 'zip_code': sb_store[key]['zip_code'] for key in dd_store.keys()])
sb_nearby['type'] = 'starbucks'
dd_nearby['type'] = 'dunkin'
sb_nearby['id'] = sb_nearby['id'].astype('str')
dd_nearby['id'] = dd_nearby['id'].astype('str')
nearby = pd.concat([sb_nearby, dd_nearby],ignore_index=True)
nearby = pd.merge(nearby, zip_code, how = 'inner', on = 'zip_code')

def search_nearby(datasets, type_list, optional_name = None, optional_para = None):
    
    #the key of the dictionay is used as the suffix for output, the value is used as a part of URL
    optional = {'':""}
    if optional_para is not None:
        for key in optional_para.keys():
            optional[key] = "&{}={}".format(key,optional_para[key])
    
    for suffix in optional.keys():
        for type in type_list:
            print("Working on {}".format(type))
            new_column = []        
            for i in range(len(datasets.values)):
                row = datasets.values[i]
                url = 'https://maps.googleapis.com/maps/api/place/radarsearch/json?location={},{}&radius=1000&type={}{}&key={}'.format(row[1], row[2], type, optional[suffix], settings.API_KEY)
                page = requests.get(url)
                soup = Soup(page.content,'html.parser')
                place = soup.get_text()
                place = json.loads(place)
                place = place['results']
                new_column.append(len(place))
                print("{}% is completed.".format(round(i/len(datasets.values)*100, 2)))
                variable_name = "{}_{}".format(type, suffix)
                datasets[variable_name] = pd.Series(np.array(new_column), index = datasets.index) 
    
    return datasets

#Define cheap and expensive as price level from 0-2 and 3-4 respectively
optional_keywords_price_level = {'cheap': {'minprice':0, 'maxprice':2}, 'expensive': {'minprice':3, 'maxprice':4}}
#Search nearby cheap and expensive restaurant and clothing store 
type_list_with_price = ['restaurant','clothing_store']
nearby = search_nearby(nearby, type_list_with_price, optional_keywords_price_level)
        
#Search other nearby facilities
type_list = ['atm', 'bakery', 'bank', 'beauty_salon', 'book_store','cafe','car_repair', 'movie_theater', 'convenience_store', 'dentist', 'florist', 'gas_station', 'gym', 'home_goods_store',\
             'hospital', 'laundry', 'liquor_store', 'museum', 'park', 'pharmacy', 'police', 'real_estate_agency', 'school', 'shopping_mall', 'stadium', 'transit_station', 'university',\
             'accounting', 'art_gallery', 'bicycle_store', 'car_dealer', 'car_rental', 'car_repair', 'church', 'city_hall', 'department_store', 'electronics_store', 'embassy', 'funeral_home',\
             'fire_station', 'hindu_temple', 'veterinary_care', 'synagogue', 'post_office', 'physiotherapist', 'parking', 'mosque', 'local_government_office', 'library']
nearby = search_nearby(nearby, type_list)
nearby.to_pickle('nearby.pkl')