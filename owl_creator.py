from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import DC, FOAF
import json
import datetime
from dateutil.parser import parse
from slugify import slugify

default_date=datetime.datetime(2000,1,1,0,0)

g = Graph()
result = g.parse("unpopulated.owl")
nm=Namespace("http://www.semanticweb.org/francisco/ontologies/2015/10/project#")

with open('steam_retrieved_data.json') as data_file:	
	data = json.load(data_file)
	comp = {}
	tags = {}
	games = {}
	for id_ in data:
		gameaux="app_"+id_.strip()
		games[gameaux] = data[id_]["name"]
		game=nm[gameaux]
		g.add((game, RDF.type, nm.Game))
		try:
			g.add((game, nm.releaseDate, Literal(parse(data[id_]["date"], default=default_date))))
		except Exception as e:
			pass

		g.add((game, nm.description, Literal(data[id_]["description"])))
		g.add((game, nm.price, Literal(data[id_]["price"])))
		for i in range(len(data[id_]["os"])):
			g.add((game, nm.OS, Literal(data[id_]["os"][i])))
		g.add((game, nm.id, Literal(id_)))
		g.add((game, nm.gameName, Literal(data[id_]["name"])))
		
		for dev in data[id_]["developers"]:
			#devURI=URIRef("http://www.semanticweb.org/francisco/ontologies/2015/10/project#comp_"+slugify(dev).upper())
			compAux = "comp_"+slugify(dev).upper()
			if compAux!="comp_":
				if compAux not in comp:
					comp[compAux] = dev
					g.add((nm[compAux],RDF.type, nm.Company))
					g.add((nm[compAux], nm.companyName, Literal(dev)))
				g.add((game, nm.developedBy, nm[compAux]))

		for pub in data[id_]["publishers"]:
			compAux = "comp_"+slugify(pub).upper()
			if compAux!="comp_":
				if compAux not in comp:
					comp[compAux] = pub
					g.add((nm[compAux],RDF.type, nm.Company))
					g.add((nm[compAux], nm.companyName, Literal(pub)))
				g.add((game, nm.publishedBy, nm[compAux]))

		for genre in data[id_]["genres"]:
			tagAux = "tag_"+slugify(genre).upper()
			if(tagAux not in tags):
				tags[tagAux] = genre.upper().strip()
				g.add((nm[tagAux],RDF.type, nm.Genre))
				g.add((nm[tagAux], nm.genreCategory, Literal(genre.upper().strip())))
			g.add((game, nm.categorizedBy, nm[tagAux]))

		if "original" in data[id_]:
			originalAux = "app_"+data[id_]["original"].strip()
			if(originalAux not in games):
				games[originalAux]=originalAux
				g.add((nm[originalAux], RDF.type, nm.Game))
			g.add((game, nm.dlcOf, nm[originalAux]))


s = g.serialize('uninfered.owl')