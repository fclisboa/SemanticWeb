import urllib3
from bs4 import BeautifulSoup
import re
import requests
import json

http = urllib3.PoolManager()
n=281
count=1
flag=True
print("{")
for i in range(n):
	try:
		url="http://store.steampowered.com/search/index.html?sort_by=Released_DESC&page=%d" %count
		#print("------------PAGE ",count,"--------------\n")
		links=[]
		r = requests.get(url, cookies={'birthtime':'722131201'})

		#print(url)
		soup = BeautifulSoup(r.text, 'lxml')
		

		ids = [link.get('data-ds-appid') for link in soup.findAll('a', href=re.compile('http://store.steampowered.com/app/')) if link.get('data-ds-appid')!=None]
		#ids=["401920"]

		for id_ in ids:
			try:
				jogo={}
				link="http://store.steampowered.com/app/%s" %id_
				tags=[]
				r=requests.get(link, cookies={'birthtime':'722131201'})
				soup = BeautifulSoup(r.text, 'lxml', )

				tags=soup.find_all('a', {"class":"app_tag"})
				tags=[tag.get_text(strip=True) for tag in tags]
				if("Hardware" in tags):
					continue
				
				if not flag:
					print(",\n")
				jogo["genres"]=tags
				flag=False
				name=soup.find('span', {"itemprop":"name"})		

				jogo["name"]=name.get_text();

				price=soup.find('meta', {"itemprop":"price"})

				if price != None:
					price=price['content']
				else:
					price=0
				jogo["price"]=price

				OS=[]
				OS.extend(soup.find_all('div', {"class":"sysreq_tab"}))
				if len(OS)==0 :
					OS.append("Windows")
				else:
					OS=[x.get_text().strip() for x in OS]
				jogo["os"]=OS
				
				devs=soup.find_all('a', href=re.compile("http://store.steampowered.com/search/\?developer="))
				devs=[d.get_text() for d in devs]
				jogo["developers"]=devs

				date=soup.find("span",{"class":"date"}).get_text()
				jogo["date"]=date

				pubs=soup.find_all('a', href=re.compile("http://store.steampowered.com/search/\?publisher="))
				pubs=[d.get_text() for d in pubs]
				jogo["publishers"]=pubs

				original=soup.find('div',{"class":"glance_details"})
				if(original !=None):
					original=original.find('a', href=re.compile("http://store.steampowered.com/app/"))
					jogo["original"]=original.get('href').split('/')[-2]
				
				description=soup.find('div',{"class":"game_area_description"})
				if description is not None:
					description=description.get_text()
				else:
					description=""
				jogo["description"]=description
				print("\"",id_,"\":",json.dumps(jogo), end="")
			except Exception as err:
				print("Erro %s" %id_)
				print(err)
	except Exception as err:
		print("Erro %d" %count)
		print(err)
	count=count+1
print("}")
