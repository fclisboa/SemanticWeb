from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
import cherrypy
import datetime
from dateutil.parser import parse
import os, os.path
import random
import sqlite3
import string
from collections import OrderedDict
from math import ceil

from jinja2 import Environment, FileSystemLoader




class HelloWorld(object):
	def __init__(self, graph):
		self.graph=graph
		self.prefixes="""PREFIX games: <http://www.semanticweb.org/francisco/ontologies/2015/10/inferredOnt#>
			PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
			PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"""

	@cherrypy.expose
	def index(self, view="games", arg="0", page="1"):

		THIS_DIR = os.path.dirname(os.path.abspath(__file__))


		j2_env = Environment(loader=FileSystemLoader(THIS_DIR),
							 trim_blocks=True)

		args={'arg':arg,'view':view,'page':int(page)}
		return j2_env.get_template('index.html').render(
			content=self.generateContent(args),
			tags=self.generateTags(),
			recommendations=self.generateRecommendations(args)
		)

	def generateRecommendations(self, args):
		if 'games_viewed' not in cherrypy.session:
			cherrypy.session['games_viewed'] = []
		if args['view']=="game":
			return self.gamesAlike(args, [args["arg"]], False)
		else:
			return self.gamesAlike(args, cherrypy.session["games_viewed"], True)

	def gamesAlike(self,args,gameList,showItSelf):
		t={}
		for g in gameList:
			gInfo = self.gameInfo(g)
			for tag in gInfo["tag_obj"]:
				if tag not in t:
					t[tag]=1
				else:
					t[tag]+=1
		
		recomendGames={}
		
		print("t",t)
		maxClaxification = sum([t[x] for x in t])
		print("g",gameList)
		for tag in t:
			result=graph.query("""%s
			SELECT ?game
				WHERE {
				?game games:categorizedBy games:%s .
				
			 }
			 """%(self.prefixes, tag))

			for x in result:
				if(showItSelf or self.unpre(x[0]) not in gameList):
					if x[0] not in recomendGames:
						result2=graph.query("""%s
						SELECT ?tag
							WHERE {
							games:%s games:categorizedBy ?tag .		
						 }"""%(self.prefixes, self.unpre(x[0])))

						recomendGames[x[0]]=[t[tag],1,len(result2)]
					else:
						recomendGames[x[0]][0]+=t[tag]
						recomendGames[x[0]][1]+=1

		rec_ordered = list(OrderedDict(sorted(recomendGames.items(), key=lambda x: -x[1][0]*(x[1][1]/x[1][2]))))
		if(len(rec_ordered) > 0):
			best = (recomendGames[rec_ordered[0]][0]*(recomendGames[rec_ordered[0]][1]/recomendGames[rec_ordered[0]][2]))/maxClaxification
			return "\n<br>".join(["<a href='/index/?view=game&arg=%s'>%s</a>, %.0f"%(self.unpre(x),self.gameInfo(self.unpre(x))["name"],(recomendGames[x][0]*(recomendGames[x][1]/recomendGames[x][2]))/maxClaxification/best*100) for x in rec_ordered[:15]])
		else:
			return ""
			
	def generateContent(self, args):
		if args['view']=="games":
			return self.generateContentGames(args)
		if args['view']=="publishers":
			return self.generatePublishers(args)
		if args['view']=="developers":
			return self.generateDevelopers(args)
		if args['view']=="categories":
			return self.generateCategories(args)
		if args['view']=="game":
			return self.generateGameInfo(args)
		if args['view']=="search":
			return self.search(args)

	def search(self,args):
		def searchNoError(l, e):
			try:
				return l.index(e)
			except Exception:
				return -1

		keywords = [(" "+args["arg"]+" ",True)]
		splOr=["game", "coperates with", "games with", "games from", "games" ,"from","with","published by","and","published","developed by", "in", "released after","released before","released on"]

		spliters=[" "+x+" " for x in splOr]
		keepWorking=True
		while(keepWorking):
			keepWorking=False
			for kIndex, k in enumerate(keywords):
				for sIndex, s in enumerate(spliters):
					if(s in k[0] and k[1]):
						begin = k[0].find(s)
						tamanho=len(s)
						newWords = [(k[0][0:begin]+" ",True),(s,False),(" "+k[0][begin+tamanho:],True)]
						keywords=keywords[:kIndex]+newWords+keywords[kIndex+1:]
						keepWorking=True
						break
				if keepWorking:
					break



		keywords = [x[0].strip() for x in keywords]
		while("" in keywords):
			keywords.remove("")

		print(keywords)
		i=0
		certeza = ""
		gameScores={}
		while(i<len(keywords)):
			certeza==""
			if(keywords[i]=="developed" or keywords[i]=="developed by"):
				certeza+="""
						?game games:developedBy ?dev .
						?dev games:companyName ?dev_name .
						FILTER (regex(lcase(str(?dev_name)), "%s", "i") ) .

				"""%keywords[i+1]
				i+=2
				continue

			if(keywords[i]=="published" or keywords[i]=="published by"):
				certeza+="""
						?game games:publishedBy ?pub .
						?pub games:companyName ?pub_name .
						FILTER (regex(lcase(str(?pub_name)), "%s", "i") ) .

				"""%keywords[i+1]
				i+=2
				continue
			
			if((keywords[i]=="games" or keywords[i]=="game") and i>0 and keywords[i-1] not in spliters):
				certeza+="""
						?game games:categorizedBy ?tag .
						?tag games:genreCategory ?tag_name .
						FILTER (regex(lcase(str(?tag_name)), "%s", "i") ) .

				"""%keywords[i-1]
				i+=1
				continue

			if(keywords[i]=="released after" or keywords[i]=="released before"):
				
				default_date=datetime.datetime(2000,1,1,0,0)
				certeza+="""
						?game games:releaseDate ?date .
						FILTER( ?date %c= "%s"^^xsd:dateTime) .

				"""%(('>' if keywords[i]=="released after" else '<'), parse(keywords[i+1], default=default_date))
				i+=1
				continue
			i+=1

		i=0

		if(len(certeza)>0):
			x="""%s
					SELECT ?game 
					
					WHERE{%s
					
					}

				"""%(self.prefixes,certeza)
			result=graph.query(x)

			for r in result:
				u=r[0]
				if u not in gameScores:
					gameScores[u]=0
				gameScores[u]+=10

		while(i<len(keywords)):
			
			if(keywords[i] not in splOr):
				for word in keywords[i].split():
					x="""%s
							SELECT ?game 
							
							WHERE{%s
							?game games:gameName ?game_name .
							FILTER (regex(lcase(str(?game_name)), "%s", "i") ) .
							}

						"""%(self.prefixes,certeza,word)
					result=graph.query(x)

					for r in result:
						u=r[0]
						if u not in gameScores:
							gameScores[u]=0
						gameScores[u]+=5

				for word in keywords[i].split():
					x="""%s
						SELECT ?game 
						
						WHERE{%s
						?game games:description ?game_name .
						FILTER (regex(lcase(str(?game_name)), "%s", "i") ) .
						}

					"""%(self.prefixes,certeza,word)
				result=graph.query(x)

				for r in result:
					u=r[0]
					if u not in gameScores:
						gameScores[u]=0
					gameScores[u]+=1

				for word in keywords[i].split():
					x="""%s
							SELECT ?game 
							
							WHERE{%s
							?game games:categorizedBy ?tagx .
							?tagx games:genreCategory ?tag_name
							FILTER (regex(lcase(str(?tag_name)), "%s", "i") ) .
							}

						"""%(self.prefixes,certeza,word)
					result=graph.query(x)

					for r in result:
						u=r[0]
						if u not in gameScores:
							gameScores[u]=0
						gameScores[u]+=3
			i+=1

			

		orderedScores=[(gameScores[x],x) for x in gameScores]
		orderedScores.sort(reverse=True)
		result=[[x[1]] for x in orderedScores]
		#print("<p>",x,"\n","\n".join([str(x[0])+" "+str(x[1]) for x in result]),"</p>")
		return "<p><h1>%s</h1></p>"%args['arg'][args['arg'].find("_")+1:]+self.genHtmlGame(-1, result, args)

	def generateGameInfo(self, args):
		if 'games_viewed' not in cherrypy.session:
			cherrypy.session['games_viewed'] = []
		
		if args["arg"] not in cherrypy.session['games_viewed']:
			cherrypy.session['games_viewed'].append(args["arg"])

		game=self.gameInfo(args["arg"])	
		
		

		return 	"""<p><h1>%s</h1><br></p><p><div class='pure-g'>
		    <div class="pure-u-16-24">
		    	<p><h3>Categories</h3>%s</a></p><br>
		    	<p><h3>Release date</h3>%s</p>
		    </div>
		    <div class="pure-u-8-24"><p>%s</p><br>
		    					<p>%s</p></div>

		</div>

		</p><br><p><h3>Available systems</h3>%s</p><br><p><h3>Price</h3>€%s</p><br><p><h3>Game description</h3>%s</p><br><p>%s</p>"""%(game["name"]," ".join(["<a href='/index/?view=games&arg=%s'>%s</a>"%(game["tag_obj"][x],game["tags"][x]) for x in range(len(game["tags"]))]), game["data"][:game["data"].find("T")],self.generateGamePublishers(args["arg"]),self.generateGameDevelopers(args["arg"]),", ".join(game["os"]), game["price"],game["description"], self.genGameDLC(args["arg"]))

	def genGameDLC(self, game):
		returned=""
		result=graph.query("""%s
			SELECT ?game ?name
				WHERE {
				games:%s games:dlcOf ?game .
				?game games:gameName ?name .
				}

			"""%(self.prefixes, game))
		for x in result:
			returned="<br><a href='/index/?view=game&arg=%s'>%s</a>"%(self.unpre(x[0]),x[1])
		if returned != "":
			return "<h3>DLC of:</h3>"+returned
		
		result=graph.query("""%s
			SELECT ?game ?name
				WHERE {
				games:%s games:originalOf ?game .
				?game games:gameName ?name .
				}

			"""%(self.prefixes, game))
		for x in result:
			returned="<br><a href='/index/?view=game&arg=%s'>%s</a>"%(self.unpre(x[0]),x[1])
		return "<h3>DLC for this game:</h3>"+returned

	def generatePartners(self, comp):
		result=graph.query("""%s
			SELECT ?comp_name ?comp
				WHERE {
				games:%s games:cooperatesWith ?comp .
				?comp games:companyName ?comp_name
				}
			"""%(self.prefixes, comp))
		
		return "\n<br>".join(["<a href='/index/?view=games&arg=%s'>%s</a>"%(self.unpre(x[1]),x[0]) for x in result])


	def generateGameDevelopers(self, game):
		result=graph.query("""%s
			SELECT distinct ?name ?pub
				WHERE {
				games:%s games:developedBy ?pub.
				?pub games:companyName ?name .
				
			 }
			 """%(self.prefixes,game))
		return "<h3>Developers</h3>"+" ".join(["<a href='/index/?view=games&arg=%s'>%s</a>"%(self.unpre(x[1]),x[0]) for x in result])

	def generateGamePublishers(self, game):

		result=graph.query("""%s
			SELECT distinct ?name ?pub
				WHERE {
				games:%s games:publishedBy ?pub.
				?pub games:companyName ?name .
				
			 }
			 """%(self.prefixes, game))
		return "<h3>Publishers</h3>"+" ".join(["<a href='/index/?view=games&arg=%s'>%s</a>"%(self.unpre(x[1]),x[0]) for x in result])

	def generatePublishers(self, args):
		counter=int([x[0] for x in graph.query("""%s
			select (count(?pub) as ?counter )
			where {
				SELECT distinct ?pub 
				WHERE {
					?game games:publishedBy ?pub
				
				}
			}"""%self.prefixes)][0])

		result=graph.query("""%s
			SELECT distinct ?name ?pub
				WHERE {
				?game games:publishedBy ?pub.
				?pub games:companyName ?name .
				
			 }
			 LIMIT 15
			 OFFSET %d
			 """%(self.prefixes,15*(args['page']-1)))
		return "<p><h1>Publishers</h1></p>"+self.genHtmlCompany(counter, result, args)

	def generateDevelopers(self, args):
		counter=int([x[0] for x in graph.query("""%s
			select (count(?dev) as ?peido )
			where {
				SELECT distinct ?dev 
				WHERE {
					?game games:developedBy ?dev
				
				}
			}
			 """%self.prefixes)][0])
		result=graph.query("""%s
			SELECT distinct ?name ?dev
				WHERE {
				?game games:developedBy ?dev.
				?dev games:companyName ?name .
				
			 }
			 LIMIT 15
			 OFFSET %d
			 """%(self.prefixes,15*(args['page']-1)))
		return "<p><h1>Developers</h1></p>"+self.genHtmlCompany(counter, result, args)

	def gameInfo(self, app_id):
		returned={"name":"","description":"","price":"","date":""}

		result=graph.query("""%s
			SELECT ?name
				WHERE { 
				games:%s games:gameName ?name .
						
			 }"""%(self.prefixes, app_id))

		for x in result:
			returned["name"]=x[0]
		
		result=graph.query("""%s
			SELECT ?desc
				WHERE { 
				games:%s games:description ?desc .				
						
			 }"""%(self.prefixes, app_id))

		for x in result:
			returned["description"]=x[0]
		
		result=graph.query("""%s
			SELECT ?price
				WHERE { 
				games:%s games:price ?price .				
						
			 }"""%(self.prefixes, app_id))

		for x in result:
			returned["price"]=x[0]
		
		result=graph.query("""%s
			SELECT ?date
				WHERE { 
				games:%s games:releaseDate ?date .
						
			 }"""%(self.prefixes, app_id))

		for x in result:
			returned["data"]=x[0]
	
		result=graph.query("""%s
			SELECT ?os
				WHERE {
				games:%s games:OS ?os 				
			 }"""%(self.prefixes, app_id))
		os=[]
		for x in result:
			os.append(str(x[0]))
		returned["os"]=os
		result=graph.query("""%s
			SELECT ?tag ?tag_name
				WHERE {
				games:%s games:categorizedBy ?tag .
				?tag games:genreCategory ?tag_name .			
			 }"""%(self.prefixes, app_id))
		tag=[]
		tag_obj=[]
		for x in result:
			tag.append(str(x[1]))
			tag_obj.append(self.unpre(x[0]))
		returned["tags"]=tag
		returned["tag_obj"]=tag_obj

		return returned


	def generateCategories(self, args):
		result=graph.query("""%s

				SELECT ?name ?value (Count(?value) as ?valueSum)
				WHERE
				{
				  ?s games:categorizedBy ?value .
				  ?value games:genreCategory ?name .
				}
				GROUP BY ?value
				Order by desc(?valueSum)"""%self.prefixes
			)
		return "<p><h1>All Categories</h1></p>"+"\n".join(["<p><a href='/index/?view=games&arg=%s'>%s</a></p>"%(self.unpre(x[1]),x[0]) for x in result])


	def generateContentGames(self, args):
		counter=0
		result=""

		if self.argType(args['arg'])=="tag":
			counter=int([x[0] for x in graph.query("""%s
			SELECT (Count(?game) as ?valueSum)
			WHERE {
				?game games:categorizedBy games:%s .
					
			 }"""%(self.prefixes,args['arg']))][0])

			result=graph.query("""%s
			SELECT ?game
				WHERE {
				?game games:categorizedBy games:%s .
				
			 }
			 LIMIT 15
			 OFFSET %d
			 """%(self.prefixes, args['arg'],15*(args['page']-1)))
			return "<p><h1>%s</h1></p>"%args['arg'][args['arg'].find("_")+1:]+self.genHtmlGame(counter, result, args)
			
	
		if self.argType(args['arg'])=="0":

			counter=int([x[0] for x in graph.query("""%s
			SELECT (Count(?game) as ?valueSum)
			WHERE {
				?game games:gameName ?name .
				?game rdf:type games:Game .
					
			 }"""%self.prefixes)][0])

			result=graph.query("""%s
			SELECT ?game
				WHERE {
				?game games:gameName ?name .
				?game rdf:type games:Game .
				
			 }
			 LIMIT 15
			 OFFSET %d
			 """%(self.prefixes,(15*(args['page']-1))))
			return "<p><h1>All games</h1></p>"+self.genHtmlGame(counter, result, args)

		if self.argType(args['arg'])=="comp":

			counter=-1
			result=graph.query("""%s
			SELECT ?companyName
				WHERE {
				games:%s games:companyName ?companyName .
				
			 }
			 """%(self.prefixes, args['arg']))

			compName=[x[0] for x in result][0]
			result=graph.query("""%s
			SELECT ?game
				WHERE {
				?game games:developedBy games:%s .
				
			 }
			 """%(self.prefixes, args['arg']))
			result2=graph.query("""%s
			SELECT ?game
				WHERE {
				?game games:publishedBy games:%s .
			 }
			 """%(self.prefixes, args['arg']))

			return "<h2>Games developed by %s\n</h2><br>\n%s\n<br>\n<h2>Games published by %s\n</h2><br>\n%s\n<br><h2>This company also worked with</h2>%s"%(compName,self.genHtmlGame(counter, result, args),compName,self.genHtmlGame(counter, result2, args), self.generatePartners(args['arg']))



	def genDivGame(self,app_id):

		game = self.gameInfo(app_id)
		return ("""
<div class="pure-g">
    <div class="pure-u-21-24">
    	<p><a href='/index/?view=game&arg=%s'><h3>%s</h3></a></p>
    	<p>%s</p>
    </div>
    <div class="pure-u-3-24"><p>%s</p></div>
</div>"""%(app_id,game["name"]," ".join(["<a href='/index/?view=games&arg=%s'>%s</a>"%(game["tag_obj"][x],game["tags"][x]) for x in range(len(game["tags"]))]),game["price"]))
		

	def genHtmlGame(self, counter, result, args):
		return("\n<hr></hr><br>".join([self.genDivGame(self.unpre(x[0])) for x in result]) + ("" if counter==-1 else self.paging(args,counter)))
		
	def genHtmlCompany(self, counter, result, args):
		return("\n<br>".join(["<a href='/index/?view=games&arg=%s'>%s</a>"%(self.unpre(x[1]),x[0]) for x in result]) + self.paging(args,counter))

	def paging(self, args, counter):
		return ("<br><br>" 
			+ " ".join(["<a href='/index/?view=%s&arg=%s&page=%i'>%s%i%s</a>"%(args['view'], args['arg'],x+1,
			"<b>"if args['page']==x+1 else"",x+1,"</b>"if args['page']==x+1 else"") for x in range(ceil(counter/15))]))

	def generateTags(self):
		result=graph.query("""%s

				SELECT ?name ?value (Count(?value) as ?valueSum)
				WHERE
				{
				  ?s games:categorizedBy ?value .
				  ?value games:genreCategory ?name .
				}
				GROUP BY ?value
				Order by desc(?valueSum)
				Limit 15"""%self.prefixes
			)
		return "\n".join(["<li><a href='/index/?view=games&arg=%s'>%s</a></li>"%(self.unpre(x[1]),x[0]) for x in result if len(x[0]) < 17])


	def argType(self,s):
		if s.find("_")==-1:
			return s
		return s[:s.find("_")]

	def unpre(self,s):
		return s[s.find("#")+1:]

if __name__ == '__main__':

	graph = Graph()
	graph.parse('inferredOnt.owl')
	conf = {
		'/': {
			'tools.sessions.on': True,
			'tools.sessions.storage_type': "file",
			'tools.staticdir.root': os.path.abspath(os.getcwd()),
			'tools.sessions.storage_path' : "sessions"
		},
		'/static': {
			'tools.staticdir.on': True,
			'tools.staticdir.dir': './public'
		}

	}

	cherrypy.quickstart(HelloWorld(graph),'/',conf)


777