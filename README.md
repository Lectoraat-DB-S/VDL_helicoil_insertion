# template-repository 🦾
codering
Tijdens het opleveren van code zien we graag dat er een README bestand wordt meegeleverd, dit maakt het gemakkelijker voor een ander om met jouw code verder te gaan of er gebruik van te maken.
Deze README beschrijft het project, wat je nodig hebt om de code te gebruiken en hoe je de code kunt gebruiken. Uiteraard kan dit ietsje afwijken aan de hand van welke taal je hebt geprogrammeerd, maar blijf het liefst zo dicht bij mogelijk bij deze standaarden.

De volgende dingen zien we graag in een README:
- beschrijving: graag zien we een korte beschrijving van je project. dus een korte uitleg wat je code doet als je het gebruikt.
De code VDL_helicoil_insertion is een HMI die gebruikt wordt om een ur10e cobot aan te sturen met een Onrobot Screwdriver en een Cobotrack. De HMI wordt voornamelijk gebruikt om de componenten vanuit een PC aan te sturen wat zorgt voor een flexibele toepassing. Dat wil zeggen een model met >300 gaten is moeilijk om handmatig via polyscope te doen, en dit wordt omzeild met dit oplossing.


- imports en versies: graag zien we een lijst met alle imports, packages, software, etc die je hebt gebruikt met de versies. Denk hierbij aan je python versie, dat je iets met "pip install" hebt geinstalleerd of dat je ubuntu 23.04 als operating system hebt gebruikt (dus ook welke versie je hebt geinstalleerd). (test dus ook je code op een andere laptop!!! hierdoor weet je zeker dat je alles genoteerd hebt)
Anaconda python interpreter py version - 3.12.9
ur-rtde 1.6.0
websocket-client 1.8.0
sockets 1.0.0
requests 2.32.3
tkinter
time
re
threading
python-socketio 5.3.0
numpy-base 2.2.2

- architectuur: graag zien we een korte beschrijving van de architectuur van je project. welke bestanden hebben welke bestanden nodig en wat kun je in welk bestand vinden.
cobotrack_interface - hierin worden alle request functions beschreven die de cobotrack aansturen en wordt gebruikt vanuit de gui_app om functies aan te roepen
gui_app - hierin wordt de logica van de HMI beschreven, onder andere alle code logica, wat wanneer aangeroepen wordt, en welke bestanden allemaal worden gebruikt
main - wordt alleen gebruikt voor de initializatie van de HMI
requests_interface - hierin worden alle screwdriver requests functies beschreven die requests sturen naar de Onrobot API, onder andere specifieke screwdriver functies te starten.
rtde_interface - hierin worden alle cobot requests functies beschreven die voor beweging en status checking zorgen over de Cobot. Ook worden hier de connectie functies beschreven.
socketio_interface - hierin wordt de SocketIO connectie protocol beschreven en geinitialiseerd voor een real-time status connectie naar de Onrobot Screwdriver

- reference: graag zien we een lijst met welke code je niet zelf hebt gemaakt of gebaseerd hebt op een ander zijn code met daarbij een link naar de originele code en een datum waarop je die code hebt geraadpleegd. Dit zorgt ervoor dat de juiste mensen credit krijgen. (let op, ook als je een functie ergens vandaan haalt en aanpast hoor je nog steeds te zeggen wie daar credit voor krijgt).
Reference: alle code is zelf geschreven aan de hand van de API beschrijvingen van de libraries, Commentaar in de code is opgesteld met gebruik van ChatGPT.

- usage: op het moment dat je extra hardware zoals een robot gebruikt is het fijn als er ook iets uitgelegd wordt over hoe je alles hebt aangesloten en opgestart. Misschien is het wel van belang dat je eerst het programma op de cobot start voordat je de python code op je laptop start.
Polyscope opstarten van de Cobot, dat kan niet vanuit de PC gedaan worden en in de instellingen zorgen dat de IP en gateway, subnet mask goed staat ingesteld voor verdere uitleg raadpleeg de onderzoek document.

- commenting: in code is het vrij normaal om comments te gebruiken om je code duidelijker te maken. Graag zien we dan ook dat dit gedaan wordt.
	- functie beschrijving: Liefst zien we dat er per functie met een comment uitgelegd wordt hoe de functie werkt en waarvoor ie bedoeld wordt (dit kan vaak in 1 zin). mocht de functie lang zijn dan zien we ook graag comments tussendoor.
	- Bestand beschrijving: Liefst zien we bovenaan elk bestand dat er een korte beschrijving staat van welke functies er in het bestand geprogrammeerd zijn.
	- Variabele beschrijving:

Een ReadMe schrijf je in Markdown. in de volgende link vind je wat voorbeelden over hoe je deze kunt stylen:
https://github.com/lifeparticle/Markdown-Cheatsheet

mocht je wat inspiratie willen kun je op de github hieronder even kijken.
https://github.com/matiassingers/awesome-readme

https://integrity.mit.edu/handbook/academic-integrity-handbook

