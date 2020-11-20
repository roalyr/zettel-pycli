#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
database_name = "my_vault"


#▒▒▒▒▒▒▒▒▒▒▒▒ CREDITS & LICENCE ▒▒▒▒▒▒▒▒▒▒▒▒▒
# https://writingcooperative.com/zettelkasten-how-one-german-
#	scholar-was-so-freakishly-productive-997e4e0ca125 - idea
# https://www.sqlitetutorial.net/sqlite-python/ - db oos
# https://stackoverflow.com/a/63529754 - md links parsing
# Personal thanks to folks from ToughSF who helped me.
# 
# MIT License
# Copyright (c) 2020 Roman Yeremenko
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


#▒▒▒▒▒▒▒▒▒▒▒▒ SCRIPT BODY ▒▒▒▒▒▒▒▒▒▒▒▒▒
#▒▒▒▒▒▒▒▒▒▒▒▒ INIT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
import os, fnmatch, shutil, pathlib, sqlite3, time, re, random
from sqlite3 import Error

path = os.path.join(os.getcwd(), database_name)
db_path = os.path.join(os.getcwd(), database_name + '_index.db')
pathlib.Path(path).mkdir(parents=True, exist_ok=True)
zettel_template_name = "_template.md"

marker_title = '[TITLE]'
marker_tags = '[TAGS]'
marker_links = '[ZETTEL LINKS]'
marker_body = '[BODY]'

#A template if you need one
zettel_template = '\n\n\n'.join([marker_title,  
marker_body, marker_tags, marker_links, ''])

#SQL schemas
create_meta_table = '''
	CREATE TABLE IF NOT EXISTS meta (
		id integer PRIMARY KEY,
		db_name text NOT NULL,
		datetime text NOT NULL,
		tot_zettels integer NOT NULL,
		tot_links integer NOT NULL,
		tot_invalid_links integer NOT NULL,
		tot_no_links integer NOT NULL,
		tot_self_links integer NOT NULL,
		tot_no_bodies integer NOT NULL,
		tot_no_titles integer NOT NULL
	); '''

create_main_table = '''
	CREATE TABLE IF NOT EXISTS main (
		id integer PRIMARY KEY,
		z_title text NOT NULL,
		z_path text NOT NULL,
		z_body text NOT NULL
	); '''

create_links_table = '''
	CREATE TABLE IF NOT EXISTS links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL,
		z_path_to integer NOT NULL
	); '''
	
create_invalid_links_table = '''
	CREATE TABLE IF NOT EXISTS invalid_links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL,
		z_path_to text NOT NULL
	); '''

create_no_links_table = '''
	CREATE TABLE IF NOT EXISTS no_links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL
	); '''
	
create_self_links_table = '''
	CREATE TABLE IF NOT EXISTS self_links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL
	); '''
	
create_empties_table = '''
	CREATE TABLE IF NOT EXISTS empties (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL
	); '''
	
create_titleless_table = '''
	CREATE TABLE IF NOT EXISTS titleless (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL
	); '''

create_tags_table = '''
	CREATE TABLE IF NOT EXISTS tags (
		id integer PRIMARY KEY,
		z_id integer NOT NULL,
		tag text NOT NULL
	); '''

insert_meta = '''
	INSERT INTO meta (
		db_name,
		datetime,
		tot_zettels,
		tot_links,
		tot_invalid_links,
		tot_no_links,
		tot_self_links,
		tot_no_bodies,
		tot_no_titles
	)
	VALUES(
		?, ?, ?, ?, ?, ?, ?, ?, ?
	) '''

insert_main = '''
	INSERT INTO main (
		z_title,
		z_path,
		z_body
	)
	VALUES(
		?, ?, ?
	) '''

insert_links = '''
	INSERT INTO links (
		z_id_from,
		z_path_to
	)
	VALUES(
		?, ?
	) '''
	
insert_invalid_links = '''
	INSERT INTO invalid_links (
		z_id_from,
		z_path_to
	)
	VALUES(
		?, ?
	) '''
	
insert_no_links = '''
	INSERT INTO no_links (
		z_id_from
	)
	VALUES(
		?
	) '''
	
insert_self_links = '''
	INSERT INTO self_links (
		z_id_from
	)
	VALUES(
		?
	) '''
	
insert_empties = '''
	INSERT INTO empties (
		z_id_from
	)
	VALUES(
		?
	) '''
	
insert_titleless = '''
	INSERT INTO titleless (
		z_id_from
	)
	VALUES(
		?
	) '''
	
insert_tags = '''
	INSERT INTO tags (
		z_id,
		tag
	)
	VALUES(
		?, ?
	) '''
	
#Just fancy stuff
banner_git	  = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒GIT MENU▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_log	  = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒LOG▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_commit   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒COMMITTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_revert   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒REVERTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_hreset   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒HARD RESETTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_main	 = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒MAIN MENU▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_zettel_ops	 = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ZETTEL ACTIONS▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
divider = '-------------------------------------------------------'
lorem = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
Phasellus mollis vulputate lobortis. Etiam auctor, massa in pulvinar 
pulvinar, nisi est consectetur arcu, ac rhoncus metus velit quis nisl. 
In nec eros in tortor faucibus egestas a vitae erat. Sed tincidunt nunc 
urna. Donec sit amet justo interdum, ullamcorper orci a, cursus dui. 
Sed et sem eget nunc tristique scelerisque ut a augue. 
Etiam leo enim, lacinia eget luctus at, aliquet vel ipsum. 
Quisque vulputate leo vitae erat sodales ultrices. Curabitur id dictum 
ligula. Praesent lectus orci, tincidunt convallis turpis sit amet, dapibus 
iaculis nisi. Integer quis gravida erat. '''


#▒▒▒▒▒▒▒▒▒▒▒▒ GIT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
git_log = "git log --branches --oneline -n 20"
git_log_1 = "git log --branches --oneline -n 1"
git_status = "git status"
git_add = "git add . && git status --short"
git_push = "git push --all"

def print_git_ops():
	print('')
	print(banner_git)
	print('() - current')
	print('(l) - log')
	print('(s) - status')
	print('')
	print('(a) - add')
	print('(c) - commit')
	print('(p) - push')
	print('')
	print('(r) - revert')
	print('(ha) - hard reset')
	print(banner_git)
	print('')
	print('(u) - launch "gitui"')
	print('(q) - quit to main')

def git_log_f():
	print(banner_log)
	os.system(git_log)
	print(banner_log)

def git_commit_f():
	print(banner_commit)
	print('Files added:')
	os.system(git_add)
	print('Current head:')
	os.system(git_log_1)
	print(banner_commit)
	commit_name = input("New commit name (' ' to abort) » ").strip()
	if commit_name =="":
		return
	inp = input("Really commit? » ").strip()
	if inp == "yes":
		git_commit = "git commit -m "+commit_name
		os.system(git_commit)
	
def git_revert_f():
	print(banner_revert)
	print('Commits:')
	os.system(git_log)
	print(banner_revert)
	commit_name = input("Revert to commit name (' ' to abort) » ").strip()
	if commit_name =="":
		return
	git_revert = "git revert "+commit_name
	os.system(git_revert)
	
def git_reset_hard_f():
	print(banner_hreset)
	print('Commits:')
	os.system(git_log)
	print(banner_hreset)
	commit_name = input("Reset to commit name (' ' to abort) » ").strip()
	if commit_name =="":
		return
	inp = input("Really? » ").strip()
	if inp == "yes":
		git_reset_hard = "git reset --hard "+commit_name
		os.system(git_reset_hard)
	
#Begin
def git_menu():
	print_git_ops()
	while True:
		print('')
		inp = input("GIT MENU ('?' for commands) » ").strip()
		print('')
				
		if inp == "l":
			git_log_f()
		elif inp == "":
			print('Current head:')
			os.system(git_log_1)
		elif inp == "s":
			os.system(git_status)
		elif inp == "a":
			os.system(git_add)
		elif inp == "c":
			git_commit_f()
		elif inp == "p":
			os.system(git_push)
		elif inp == "r":
			git_revert_f()
		elif inp == "ha":
			git_reset_hard_f()
		elif inp == "?":
			print_git_ops()
		elif inp == "u":
			os.system('gitui')
		elif inp == "q":
			break
			
			

#▒▒▒▒▒▒▒▒▒▒▒▒ FILE OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def gen_template():
	f = open(path + "/" + zettel_template_name, "w")
	f.write(zettel_template)
	f.close()
	
def make_test_batch():
	inp_num = input("enter the amount of zettels to make » ").strip()
	inp_links = input("enter the amount of links per zettel to make » ").strip()
	inp_corr = input("enter the amount of correct zettels (0.0 .. 1.0) » ").strip()
	
	#perfect zettels
	for i in range(int(inp_num)):
		frnd = random.random() 
		frnd2 = random.random() 
		frnd3 = random.random() 
		if frnd <= float(inp_corr):
			links = ''
			try:
				#generate links, avoiding self-linking
				for j in range(int(inp_links)):
					rnd = random.randrange(int(inp_num))
					if rnd == i:
						rnd += 1
					if rnd == int(inp_num):
						rnd -= 2
					links += '[Test link '+str(j)+']('+str(rnd)+'.md)\n'
			except:
				pass
			
			zettel_template_test = marker_title + '\n' + 'Test zettel № ' + str(i) \
			+ '\n\n' + marker_body + '\n' + lorem + '\n\n' + marker_tags + '\n' \
			+ "test, zettel batch, performance" + '\n\n' + marker_links + '\n' + links
		
		else:
			#bad zettels
			links = ''
			try:
				if frnd3 < 0.25:
					for j in range(int(inp_links)):
						rnd = random.randrange(int(inp_num))
						links += '[Test link '+str(j)+']('+str(rnd)+'.md)\n'
				elif frnd2 < 0.5 and frnd >= 0.25:
					links += '[some](bronek links)'
				elif frnd < 0.75 and frnd >= 0.5:
					links += '[Self link '+str(j)+']('+str(i)+'.md)\n'
				else: 
					pass
			except:
				pass
			
			if frnd < 0.33:
				zettel_template_test = marker_title + '\n'\
				+ '\n\n' + marker_body + '\n' + lorem + '\n\n' + marker_tags + '\n' \
				+ "test, zettel batch, performance" + '\n\n' + marker_links + '\n' + links
				
			elif frnd3 < 0.66 and frnd >= 0.33:
				zettel_template_test = marker_title + '\n' + 'Test zettel № ' + str(i) \
				+ '\n\n' + marker_body + '\n\n' + marker_tags + '\n' \
				+ "test, zettel batch, performance" + '\n\n' + marker_links + '\n' + links
			
			elif frnd2 <= 1.0 and frnd >= 0.66:
				zettel_template_test = marker_title + '\n'\
				+ '\n\n' + marker_body + '\n' + marker_tags + '\n' \
				+ "test, zettel batch, performance" + '\n\n' + marker_links + '\n' + links
		
		
		f = open(path + "/" + str(i) + '.md', "w")
		f.write(zettel_template_test)
		f.close()
	
def make_new():
	inp = input("enter zettel name » ").strip()
	f = open(path + "/" + inp + '.md', "w")
	f.write(zettel_template_test)
	f.close()
	return inp



#▒▒▒▒▒▒▒▒▒▒▒▒ PARSING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def find_md_links(md):
	INLINE_LINK_RE = re.compile(r'\(([^)]+)\)')
	links = list(INLINE_LINK_RE.findall(md))
	return links

def find_comma_separated(md):
	COMMA_SEP_CONT = re.compile(r'(.+?)(?:,\s*|$)')
	text = list(COMMA_SEP_CONT.findall(md))
	return text
	
def parse_zettel_metadata(z_path):
	#expected parsed data
	data = {
		'title' : '',
		'body' : '',
		'tags' : [],
		'links' : [],
	}
	
	# open the file and read through it line by line
	f = open(z_path, 'r')
	
	#a switch flag to read links in tge end of the file
	reading_title = False
	reading_body = False
	reading_links = False
	reading_tags = False
	
	#parse keywords
	for line in f:
		
		if marker_body in line:
			reading_title = False
			reading_body = True
			reading_tags = False
			reading_links = False
			continue
	
		if marker_title in line:
			reading_title = True
			reading_body = False
			reading_tags = False
			reading_links = False
			continue
		
		if marker_tags in line:
			reading_title = False
			reading_body = False
			reading_tags = True
			reading_links = False
			continue
	
		if marker_links in line:
			reading_title = False
			reading_body = False
			reading_tags = False
			reading_links = True
			continue
		
		if reading_title:
			data['title'] += line.strip()
			
		if reading_body:
			data['body'] += line.strip()
			
		if reading_tags:
			data['tags'] += find_comma_separated(line)
			
		if reading_links:
			data['links'] += find_md_links(line)
	
	return data
	
	
#▒▒▒▒▒▒▒▒▒▒▒▒ DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def query_db(exec_line):
	found = []
	conn = None
	try:
		conn = sqlite3.connect(db_path)
	except Error as e:
		print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				c.execute(exec_line)
				found = c.fetchall()
			except Error as e:
				print(e)
			conn.close()
			return found

def print_db_meta():
	meta = query_db("SELECT * FROM meta")
	print('database name:', meta[0][1])
	print('created:', meta[0][2])
	print('total number of zettels:', meta[0][3])
	print('total number of links:', meta[0][4])
	print(divider)
	print('warnings:')
	print('invalid links:', meta[0][5])
	print('zettels without links:', meta[0][6])
	print('zettels that link to themselves:', meta[0][7])
	print('empty zettels:', meta[0][8])
	print('zettels without titles:', meta[0][9])

def update_db():
	#remove existing db
	try:
		os.remove(db_path)
		print('clearing previous database, updating...')
	except:
		print('no database to clear, creating...')
	
	conn = None
	try:
		conn = sqlite3.connect(db_path)
	except Error as e:
		print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				
				#create tables
				c.execute(create_meta_table)
				c.execute(create_main_table)
				c.execute(create_links_table)
				c.execute(create_invalid_links_table)
				c.execute(create_no_links_table)
				c.execute(create_self_links_table)
				c.execute(create_tags_table)
				c.execute(create_empties_table)
				c.execute(create_titleless_table)
				
				#populate tables
				time_start = time.time()
				links = []
				tot_links = 0
				tot_invalid_links = 0
				tot_self_links = 0
				tot_no_links = 0
				tot_no_bodies = 0
				tot_no_titles = 0

				#main table
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name:
							continue
							
						full_path = os.path.join(root, name)
						parsed = parse_zettel_metadata(full_path)
						
						z_path = name
						z_title = parsed['title']
						z_body = parsed['body']
						tags = parsed['tags']
						
						#first write main table
						c.execute(insert_main, (z_title, z_path, z_body))
						
						#get the current zettel id
						c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (name,))
						current_zettel_id = c.fetchall()[0][0]
						
						#store metadata
						for tag in tags:
							c.execute(insert_tags, (current_zettel_id, tag,))
							
						#store errors
						if z_body == '':
							c.execute(insert_empties, (current_zettel_id,))
							tot_no_bodies += 1
						if z_title == '':
							c.execute(insert_titleless, (current_zettel_id,))
							tot_no_titles += 1
							
				#links must be done only once main tabe is populated
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name:
							continue
							
						full_path = os.path.join(root, name)
						parsed = parse_zettel_metadata(full_path)
						
						links = parsed['links']
						tot_links += len(links)
						
						#get the current zettel id
						c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (name,))
						current_zettel_id = c.fetchall()[0][0]
						
						#see if links point out to existing nodes
						for z_path_to in links:
							#destination zettel
							c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (z_path_to,))
							found_zettel = c.fetchall()
							if found_zettel:
								valid_zettel_id = found_zettel[0][0]
								
								#make sure it doesn't point to itself
								if valid_zettel_id != current_zettel_id:
									c.execute(insert_links, (current_zettel_id, valid_zettel_id,))
								else:
									c.execute(insert_self_links, (current_zettel_id,))
									tot_self_links += 1
							else:
								c.execute(insert_invalid_links, (current_zettel_id, z_path_to,))
								tot_invalid_links += 1
						if links == []:
							c.execute(insert_no_links, (current_zettel_id,))
							tot_no_links += 1
				
				tot_zettels = len(files)
				
				#write meta
				dt_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
				c.execute(insert_meta, (database_name, dt_str, tot_zettels, tot_links, tot_invalid_links, tot_no_links, 
					tot_self_links, tot_no_bodies, tot_no_titles,))
				
				conn.commit()
				time_end = time.time()
				print('database rebuilt in:', time_end - time_start, 's')
				print_db_meta()
					
			except Error as e:
				print(e)
			conn.close()



#▒▒▒▒▒▒▒▒▒▒▒▒ ANALYSIS OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def print_search_commands():
	print("'number' - select entry")
	print("(c) - clear search query")
	
def print_entries(entry, val):
	z_title = entry[1]
	z_path = entry[2]
	z_id = entry[0]
	if z_title != '':
		print()
		print('selected:', str(val)+'.', z_path)
		print(' ╰ ' + z_title)
	else:
		print()
		print('selected:', str(val)+'.', z_path)
	print_zettel_ops()
	zettel_ops(z_id)

def increm_input_title_name():
	name = ''
	inp = ''
	entities = []
	while True:
		num = 0
		inp = input('srarching for: ' + name + " « ")
		#see if we are entering the name or command
		if inp != ':':
			os.system('clear')
			print(divider)
			name += inp
		
		#show all if no input
		if name == '':
			get_all = "SELECT * FROM main"
			entries = query_db(get_all)
		#or find by name or title
		if name != '':
			get_by_name = "SELECT * FROM main WHERE z_path LIKE '%"+name+"%' OR z_title LIKE '%"+name+"%'"
			entries = query_db(get_by_name)
		
		#commands sub-menu
		if inp == ':':
			print(divider)
			print_search_commands()
			i = input(" » ")
			print()
			print(divider)
			try:
				val = int(i)
				print_entries(entries[val], val)
			except:
				pass
			finally:
				if i == "c":
					name = ''
					inp = ''
			os.system('clear')
			continue
		
		if len(entries) > 1:
			for entry in entries:
				if entry[1] != '':
					title = entry[1]
					print()
					print(str(num)+'.', entry[2])
					print(' ╰ ' + title)
				else:
					print()
					print(str(num)+'.', entry[2])
				num += 1
				
			print(divider)
			print('total search hits:', len(entries))
			print('keep narrowing your search by entering more characters')
			print("or enter ':' for search tools")
			print(divider)
			
		elif len(entries) == 1: 
			print_entries(entries[0], '')
		
		#break if neither name matches
		elif len(entries) == 0: 
			print('no zettel found, returning to main menu')
			print(divider)
			return
		
		
def list_corrupt_links():
	get_all = "SELECT * FROM invalid_links"
	entries = query_db(get_all)
	if entries == []:
		return False
		
	same_file = False
	name_previous = ''
	num = 0
	for entry in entries:
		get_file_name = "SELECT * FROM main WHERE id =" + str(entry[1])
		name = query_db(get_file_name)[0][2]

		if name == name_previous:
			same_file = True
			
		if same_file:
			print('   └─', entry[2])
			same_file = False
		else:
			print()
			print(str(num)+'.', 'file:', name)
			print('   corrupt links:')
			print('   └─', entry[2])
			num += 1
		
		name_previous = name
	return True
		
def list_zettels(exec_str):
	entries = query_db(exec_str)
	if entries == []:
		return False
	num = 0
	for entry in entries:
		get_file_name = "SELECT * FROM main WHERE id =" + str(entry[1])
		name = query_db(get_file_name)[0][2]
		print(str(num)+'.', 'file:', name)
		num += 1
	return True
	
def print_zettel_body(z_id):
	get_body = "SELECT * FROM main WHERE id =" + str(z_id)
	body = query_db(get_body)
	print(body[0][3])
	
	

#▒▒▒▒▒▒▒▒▒▒▒▒ ZETTEL OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def print_zettel_ops():
	print('')
	print(banner_zettel_ops)
	print('() - read current zettel')
	print(banner_zettel_ops)
	print('')
	print('(q) - quit')
	
def zettel_ops(z_id):
	while True:
		inp = input("ZETTEL OPS ('?' for commands) » ").strip()
		if inp == "":
			os.system('clear')
			print(divider)
			print_zettel_body(z_id)
			print(divider)
		elif inp == "?":
			print_zettel_ops()
		elif inp == 'q':
			return
		
		
			
#▒▒▒▒▒▒▒▒▒▒▒▒ FUNCTION WRAPPERS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def sync():
	print(divider)
	update_db()
	print(divider)
	
def info():
	print(divider)
	if os.path.isfile(db_path):
		print_db_meta()
		print(divider)
	else:
		print('initiate database with update command')
		print(divider)
	
def tree():
	os.system('tree'+' '+path)
	print(divider)
	print('tree rendred')
	print(divider)
	
def make_template():
	gen_template()
	print(divider)
	print('generated a non-indexed template zettel:', zettel_template_name)
	print(divider)

def find_zettel():
	print(divider)
	print('start entering zettel title or filename parts') 
	print('(character, parts of words, or whole name)')
	print('and get incremental results. Enter - to refresh')
	print(divider)
	increm_input_title_name()
	
def review():
	errors = False
	print(divider)
	print('checking your zettels...')
	print(divider)
	print()
	if list_zettels("SELECT * FROM titleless"):
		print(divider)
		print('there are zettels without titles listed above, inspect')
		print(divider)
		print()
		errors = True
		
	if list_zettels("SELECT * FROM empties"):
		print(divider)
		print('there are zettels without text listed above, fill them')
		print(divider)
		print()
		errors = True
		
	if list_zettels("SELECT * FROM no_links"):
		print(divider)
		print('there are unlinked zettels listed above, link them')
		print(divider)
		errors = True
	
	if list_zettels("SELECT * FROM self_links"):
		print(divider)
		print('there are zettels linking to themselves listed above')
		print(divider)
		errors = True
	
	if list_corrupt_links():
		print(divider)
		print('there are corrupt links in your zettels, review them')
		print(divider)
		errors = True
		
	if not errors:
		print('all good, no corrupt links or unlinked zettels')
		print(divider)
	
def make_new_zettel():
	zettel_name = make_new()
	print(divider)
	print('generated a new empty zettel from template:', zettel_name)
	print("don't forget to update the database")
	print(divider)
	
def make_test_zettels():
	print(divider)
	print('make sure you backed up your journal folder')
	make_test_batch()
	print(divider)
	print('generated a number of test zettels')
	print("don't forget to update the database")
	print(divider)
	
		
		
#▒▒▒▒▒▒▒▒▒▒▒▒ MAIN MENU ▒▒▒▒▒▒▒▒▒▒▒▒▒
def print_main_ops():
	print('')
	print(banner_main)
	print('() - show statistics')
	print('(u) - update the database')
	print('(f) - incrementally find zettel to enter the graph')
	print('(r) - review zettels for errors in links')
	print('(tree) - use "tree" command to show files')
	print()
	print('(n) - make new empty zettel')
	print('(temp) - generate a template zettel')
	print('(test) - generate a batch of test zettels')
	print(banner_main)
	print('')
	print('(t) - git menu')
	print('(q) - quit')
		
def main_menu():
	print_main_ops()
	
	while True:
		print('')
		inp = input("MAIN MENU ('?' for commands) » ").strip()
		print('')
				
		if inp == "":
			os.system('clear')
			info()
		if inp == "u":
			os.system('clear')
			sync()
		if inp == "n":
			os.system('clear')
			make_new_zettel()
		if inp == "f":
			os.system('clear')
			find_zettel()
		if inp == "r":
			os.system('clear')
			review()
		if inp == "tree":
			os.system('clear')
			tree()
		if inp == "temp":
			os.system('clear')
			make_template()
		if inp == "test":
			os.system('clear')
			make_test_zettels()
		elif inp == "t":
			os.system('clear')
			git_menu()
		elif inp == "?":
			print_main_ops()
		elif inp == "q":
				quit()

#Start 
os.system('clear')
while True:
	main_menu()
