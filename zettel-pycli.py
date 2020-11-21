#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
database_name = "my_vault" # default name for new databases
default_editor = "nano" #enter anything that suits your preference

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
import os, fnmatch, shutil, pathlib, sqlite3, time, re, random, tempfile, subprocess
from sqlite3 import Error

path = os.path.join(os.getcwd(), database_name)
current_db_path = os.path.join(os.getcwd(), database_name + '.db')
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
		db_name text NOT NULL, datetime text NOT NULL,
		tot_zettels integer NOT NULL, tot_links integer NOT NULL,
		tot_invalid_links integer NOT NULL, tot_no_links integer NOT NULL,
		tot_self_links integer NOT NULL, tot_no_bodies integer NOT NULL,
		tot_no_titles integer NOT NULL
	); '''
create_main_table = '''
	CREATE TABLE IF NOT EXISTS main (
		id integer PRIMARY KEY, z_title text NOT NULL,
		z_path text NOT NULL, z_body text NOT NULL
	); '''
create_links_table = '''
	CREATE TABLE IF NOT EXISTS links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL, z_path_to integer NOT NULL
	); '''
create_invalid_links_table = '''
	CREATE TABLE IF NOT EXISTS invalid_links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL, z_path_to text NOT NULL
	); '''
create_no_links_table = '''
	CREATE TABLE IF NOT EXISTS no_links (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_self_links_table = '''
	CREATE TABLE IF NOT EXISTS self_links (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_empties_table = '''
	CREATE TABLE IF NOT EXISTS empties (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_titleless_table = '''
	CREATE TABLE IF NOT EXISTS titleless (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_tags_table = '''
	CREATE TABLE IF NOT EXISTS tags (
		id integer PRIMARY KEY, z_id integer NOT NULL, tag text NOT NULL
	); '''
create_tags_list_table = '''
	CREATE TABLE IF NOT EXISTS tags_list (
		id integer PRIMARY KEY, tag text NOT NULL, UNIQUE ( tag )
	); '''

insert_main = '''INSERT INTO main ( z_title, z_path, z_body ) VALUES ( ?, ?, ? ) '''
insert_links = '''INSERT INTO links ( z_id_from, z_path_to ) VALUES ( ?, ? ) '''
insert_invalid_links = '''INSERT INTO invalid_links ( z_id_from, z_path_to ) VALUES ( ?, ? ) '''
insert_no_links = '''INSERT INTO no_links ( z_id_from ) VALUES ( ? ) '''
insert_self_links = '''INSERT INTO self_links ( z_id_from ) VALUES ( ? ) '''
insert_empties = '''INSERT INTO empties ( z_id_from ) VALUES ( ? ) '''
insert_titleless = '''INSERT INTO titleless ( z_id_from ) VALUES ( ? ) '''
insert_tags = '''INSERT INTO tags ( z_id, tag ) VALUES ( ?, ? ) '''
insert_tags_list = '''INSERT OR IGNORE INTO tags_list ( tag ) VALUES ( ? ) ''' #if not n table
insert_meta = '''
	INSERT INTO meta (
		db_name, datetime, tot_zettels, tot_links, tot_invalid_links,
		tot_no_links, tot_self_links, tot_no_bodies, tot_no_titles
	) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? ) ''' #add tags num
	
#Just fancy stuff
banner_log	  = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ LOG ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_commit   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ COMMITTING ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_revert   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ REVERTING ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_hreset   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ HARD RESETTING ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
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

def git_log_f(): print(banner_log); os.system(git_log); print(banner_log)

def git_commit_f():
	print(banner_commit); print('Files added:'); os.system(git_add)
	print('Current head:'); os.system(git_log_1); print(banner_commit)
	commit_name = input("New commit name (' ' to abort) » ").strip()
	if commit_name =="": return
	inp = input("Really? (type 'yes') » ").strip()
	if inp == "yes":
		git_commit = "git commit -m "+commit_name
		os.system(git_commit)
	
def git_revert_f():
	print(banner_revert); print('Commits:'); os.system(git_log); print(banner_revert)
	commit_name = input("Revert to commit name (' ' to abort) » ").strip()
	if commit_name =="": return
	git_revert = "git revert "+ commit_name; os.system(git_revert)
	
def git_reset_hard_f():
	print(banner_hreset); print('Commits:'); os.system(git_log); print(banner_hreset)
	commit_name = input("Reset to commit name (' ' to abort) » ").strip()
	if commit_name =="": return
	inp = input("Really? (type 'yes') » ").strip()
	if inp == "yes":
		git_reset_hard = "git reset --hard "+commit_name
		os.system(git_reset_hard)
	
#Begin
def git_menu():
	os.system('clear'); print_git_ops()
	while True:
		inp = input("GIT MENU ('?' for commands) » ").strip()
		os.system('clear')
		if inp == "": print('Current head:'); os.system(git_log_1)
		elif inp == "l": git_log_f()
		elif inp == "s": os.system(git_status)
		elif inp == "a": os.system(git_add)
		elif inp == "c": git_commit_f()
		elif inp == "p": os.system(git_push)
		elif inp == "r": git_revert_f()
		elif inp == "ha": git_reset_hard_f()
		elif inp == "?": print_git_ops()
		elif inp == "u": os.system('gitui')
		elif inp == "q": break

#▒▒▒▒▒▒▒▒▒▒▒▒ FILE OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def gen_template():
	f = open(path + "/" + zettel_template_name, "w")
	f.write(zettel_template)
	f.close()
	
def make_test_batch():
	print_test_warn()
	try:
		inp_num = int(input("enter the amount of zettels to make » ").strip())
		inp_links = int(input("enter the amount of links per zettel to make » ").strip())
		inp_corr = float(input("enter the amount of correct zettels (0.0 .. 1.0) » ").strip())
	except: print_test_failed(); return False #failed
	#perfect zettels
	for i in range(inp_num):
		frnd = random.random(); frnd2 = random.random(); frnd3 = random.random() 
		if frnd <= inp_corr:
			links = ''
			try: #generate links, avoiding self-linking
				for j in range(inp_links):
					rnd = random.randrange(inp_num)
					if rnd == i: rnd += 1
					if rnd == inp_num: rnd -= 2
					links += '[Test link '+str(j)+']('+str(rnd)+'.md)\n'
			except: pass
			zettel_template_test = marker_title + '\n' + 'Test zettel № ' + str(i) \
			+ '\n\n' + marker_body + '\n' + lorem + '\n\n' + marker_tags + '\n' \
			+ "test, zettel batch, performance" + '\n\n' + marker_links + '\n' + links
		else: #bad zettels
			links = ''
			try: #make some wrong links
				if frnd3 < 0.25:
					for j in range(inp_links):
						rnd = random.randrange(inp_num)
						links += '[Test link '+str(j)+']('+str(rnd)+'.md)\n'
				elif frnd2 < 0.5 and frnd >= 0.25: links += '[some](bronek links)'
				elif frnd < 0.75 and frnd >= 0.5: links += '[Self link '+str(j)+']('+str(i)+'.md)\n'
				else: pass
			except: pass
			
			if frnd < 0.33: #make some wrong zettels
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
		if not os.path.exists(path): os.mkdir(path)
		f = open(path + "/" + str(i) + '.md', "w")
		f.write(zettel_template_test); f.close()
	return True #succeeded
	
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
	data = {'title' : '', 'body' : '', 'tags' : [], 'links' : [], }
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
		if reading_title: data['title'] += line.strip()
		if reading_body: data['body'] += line.strip()
		if reading_tags: data['tags'] += find_comma_separated(line)
		if reading_links: data['links'] += find_md_links(line)
	return data
	
#▒▒▒▒▒▒▒▒▒▒▒▒ DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def query_db(exec_line, db_path):
	found = []; conn = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				c.execute(exec_line)
				found = c.fetchall()
			except Error as e: print(e)
			conn.close(); return found

def import_to_db():
	print('folders with nested sub-folders are not supported')
	inp = input('Provide local folder name to import from » ').strip()
	if not os.path.isdir(inp):
		print('wrong folder name, aborting'); return #failed
	dt_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
	dt_str_file = time.strftime("%d%b%Y%H%M%S", time.localtime())
	db_name_imported = os.path.join('imported_' + inp + '_' + dt_str_file + '.db')
	conn = None
	try: conn = sqlite3.connect(db_name_imported)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				time_start = time.time()
				c = conn.cursor()
				#create tables
				c.execute(create_meta_table); c.execute(create_main_table)
				c.execute(create_links_table); c.execute(create_invalid_links_table)
				c.execute(create_no_links_table); c.execute(create_self_links_table)
				c.execute(create_tags_table); c.execute(create_empties_table)
				c.execute(create_titleless_table); c.execute(create_tags_list_table);
				#populate tables
				links = []; tot_links = 0; tot_tags = 0; tot_invalid_links = 0; 
				tot_no_links = 0; tot_no_bodies = 0; tot_no_titles = 0; tot_self_links = 0
				#main table
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name: continue #skip it
						full_path = os.path.join(root, name)
						parsed = parse_zettel_metadata(full_path)
						z_path = name
						z_title = parsed['title']
						z_body = parsed['body']
						tags = parsed['tags']
						#first write main table
						c.execute(insert_main, (z_title, z_path, z_body))
						#get the current zettel id
						c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (z_path,))
						current_zettel_id = c.fetchall()[0][0]
						#store metadata
						for tag in tags:
							c.execute(insert_tags, (current_zettel_id, tag,))
							c.execute(insert_tags_list, (tag,))
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
						if name == zettel_template_name: continue #skip it
						full_path = os.path.join(root, name)
						parsed = parse_zettel_metadata(full_path)
						links = parsed['links']
						tot_links += len(links)
						#get the current zettel id
						c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (z_path,))
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
				c.execute(insert_meta, (db_name_imported, dt_str, tot_zettels, tot_links, tot_invalid_links, tot_no_links, 
					tot_self_links, tot_no_bodies, tot_no_titles,))
				#write all
				conn.commit()
				time_end = time.time()
				print('database rebuilt in:', time_end - time_start, 's')
				print(divider)
				print_db_meta(db_name_imported)
				print(divider)
				print('to use the database rename it to match:', database_name+'.db')
			except Error as e: print(e)
			conn.close()
			
def init_new_db():
	#check and abort
	if os.path.isfile(current_db_path):
		print(divider)
		print('a database like this already exists, aborting')
		print(divider)
		return
	dt_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
	conn = None
	try: conn = sqlite3.connect(current_db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				#create tables
				c.execute(create_meta_table); c.execute(create_main_table)
				c.execute(create_links_table); c.execute(create_invalid_links_table)
				c.execute(create_no_links_table); c.execute(create_self_links_table)
				c.execute(create_tags_table); c.execute(create_empties_table)
				c.execute(create_titleless_table); c.execute(create_tags_list_table);
				#write meta
				c.execute(insert_meta, (database_name, dt_str, 0, 0, 0, 0, 0, 0, 0,))
				conn.commit()
				print_db_meta(database_name)
			except Error as e: print(e)
			conn.close()
			
#▒▒▒▒▒▒▒▒▒▒▒▒ WRITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def write_ext(option):
	written = ''
	with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
		try: subprocess.call([option, tf.name])
		except: print('no command found:', option); return written #failed
		finally:
			tf.seek(0); written = tf.read().decode("utf-8")
	return written #succeeded
	
def make_new_zettel():
	z_title = ''
	z_body = ''
	z_tags = []
	z_links = []
	os.system('clear')
	print(divider)
	while z_title == '': z_title = input("enter zettel title » ").strip()
	while z_body == '':
		print_writer_options()
		inp = input("Select editor » ").strip()
		os.system('clear')
		if inp == '': z_body = write_ext(default_editor)
		elif inp == 'v': z_body = write_ext('vim')
		elif inp == 'n': z_body = write_ext('nano')
		elif inp == 'e': z_body = write_ext('emacs')
		elif inp == "q": return
	
	#testung
	#return the list of link which should be written later
	while True:
		print_links_select()
		inp = input("Enter to continue, 'q' to finish selecting » ").strip()
		os.system('clear')
		if inp == "q": break
		try: 
			z_links.append(search_zettel('')[0])
			z_links = list(dict.fromkeys(z_links)) #de-duplicate links list
			print('Selected links:', z_links)
		except: pass
	#return the list of tags which should be written later
	while True:
		print_tags_select()
		inp = input("Enter to continue, 'q' to finish selecting » ").strip()
		os.system('clear')
		if inp == "q": break
		try: 
			z_tags.append(find_tags_by_input()[1])
			z_tags = list(dict.fromkeys(z_tags)) #de-duplicate links list
			print('Selected tags:', z_tags)
		except: pass
	#preview
	print(divider)
	print('Title:',z_title)
	print()
	print('Text:', z_body)
	print()
	print('Tags:', z_tags)
	print()
	print('Links:', z_links)
	print(divider)

#▒▒▒▒▒▒▒▒▒▒▒▒ READING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def read_z_body(z_id):
	get = "SELECT DISTINCT * FROM main WHERE id =" + str(z_id)
	return query_db(get, current_db_path)[0][3]

def read_z_title(z_id):
	get = "SELECT DISTINCT * FROM main WHERE id =" + str(z_id)
	return query_db(get, current_db_path)[0][1]
	
def read_z_tags(z_id):
	get = "SELECT DISTINCT * FROM main WHERE id =" + str(z_id)
	return query_db(get, current_db_path)[0][1]
	
def read_z_links(z_id):
	get = "SELECT DISTINCT * FROM main WHERE id =" + str(z_id)
	return query_db(get, current_db_path)[0][1]

def read_whole_zettel(z_id):
	return marker_title + '\n' + read_z_title(z_id) + '\n\n' \
	+ marker_body+ '\n' + read_z_body(z_id) + '\n\n' \
	+ marker_tags+ '\n' + read_z_tags(z_id) + '\n\n' \
	+ marker_links+ '\n' + read_z_links(z_id)

def read_tags_list_table():
	get_all = "SELECT DISTINCT * FROM tags_list"
	return query_db(get_all, current_db_path)

def read_tags_table_like(name):
	get_ids = "SELECT * FROM tags WHERE tag LIKE '%"+name+"%' "
	return query_db(get_ids, current_db_path)
			
def read_main_table():
	get_all = "SELECT * FROM main"
	return query_db(get_all, current_db_path)

#▒▒▒▒▒▒▒▒▒▒▒▒ SEARCH OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def search_zettel(flag):
	if flag == '':
		while True:
			print('(n) - by zettel name (title)')
			print('(t) - by tag')
			inp = input("How to search? ('q' to return) » ")
			if inp == 'n': flag = 'name'; break
			if inp == 't': flag = 'tag'; break
			if inp == 'q': return
	entry = (); entries = []
	while True:
		s = find_zettel(flag)
		if s['found'] or s['stop']: 
			os.system('clear')
			if s['stop']: break
			if s['found']: entries.append(s['found'])
			#print_selected_zettels(entries)
			inp = input("Search for more? 'q' to stop and return » ")
			if inp == 'q': break
	print(divider)
	return entry
	
def print_found_zettels(entry, val):
	z_title = entry[1]
	z_id = entry[0]
	print('selected:', str(val)+'.', z_title)
	print_zettel_ops()
	zettel_ops(z_id, z_title)

def print_found_tags(entry, val):
	tag = entry[1]
	tag_id = entry[0]
	print('selected:', str(val)+'.', tag)
	print_tag_ops()
	tag_ops(tag_id, tag)
	
def print_many_or_return(entries):
	num = 1
	if len(entries) > 1:
		for entry in entries:
			print(str(num)+'.', entry[1])
			num += 1
		print(divider); print('total search hits:', len(entries)); print_searching()
	elif len(entries) == 0: 
		print("no zettel found, ':' for options"); print(divider)
	elif len(entries) == 1: 
		print_found_zettels(entries[0], '')
		return entries[0] #return what was found by narrowing down

def search_sub_menu(s):
	print_search_commands()
	i = input(" » "); print(divider)
	try: print_found_zettels(s['entries'][int(i)-1], int(i)); s['entries'][int(i)-1]
	except: pass
	finally:
		if i == "c": s['name'] = ''; s['inp'] = ''; s['entries'] = read_main_table() #reset
		if i == "q": s['stop'] = True
	return s

def find_zettel(flag):
	s = {'found': None, 'name': '', 'inp': '', 'entries': [], 'stop': False}
	s['entries'] = read_main_table()
	while True:
		os.system('clear'); print(divider); 
		if s['inp'] != ':': s['name'] += s['inp']
		if flag == 'tag': list_all_tags()
		if flag == 'name': 
			get_by_name = "SELECT * FROM main WHERE z_title LIKE '%"+s['name']+"%' "
			s['entries'] = query_db(get_by_name, current_db_path)
		elif flag == 'tag':
			s['entries'].clear() #reset
			if s['name'] != '': #if entereg something - fing by tag
				tagged = read_tags_table_like(s['name'])
				for tagged_entry in tagged:
					found_id = tagged_entry[1]
					get_all_by_tag = "SELECT * FROM main WHERE id =" + str(found_id)
					entry = query_db(get_all_by_tag, current_db_path)[0]
					s['entries'].append(entry)
				s['entries'] = list(dict.fromkeys(s['entries'])) #dedup
			else: s['entries'] = read_main_table() #or show all
		s['found'] = print_many_or_return(s['entries'])
		if s['inp'] == ':': 
			s = search_sub_menu(s); 
			os.system('clear'); print(divider);
			if flag == 'tag': list_all_tags()
			print_many_or_return(s['entries']); 
		if s['found'] or s['stop']: return s
		s['inp'] = input('searching zettel by ' + flag +': '+ s['name'] + " « ")
		
def find_tags_by_input():
	tag = ''; inp = ''; entities = []
	while True:
		os.system('clear'); print(divider); list_all_tags()
		num = 1
		#see if we are entering the name or command
		if inp != ':': tag += inp
		#show all if no input, or find by name or title
		if tag == '':
			entries = read_tags_list_table()
		else:
			get_by_tag = "SELECT DISTINCT * FROM tags_list WHERE tag LIKE '%"+tag+"%' "
			entries = query_db(get_by_tag, current_db_path)
		#search sub-menu
		if inp == ':':
			selected_entry = []
			print_search_commands()
			i = input(" » ")
			print(divider)
			try: 
				print_found_tags(entries[int(i)-1], int(i))
				return entries[int(i)-1] #return the one selected from list
			except: pass
			finally:
				if i == "c": tag = ''; inp = ''; entries = query_db(get_all, current_db_path) 
			os.system('clear')
		entry = print_many_or_return(entries)
		if entry: return entry
		#else store in tags table if none
		inp = input('srarching for tag: ' + tag + " « ")

#▒▒▒▒▒▒▒▒▒▒▒▒ LIST OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def list_by_tag(tag_id):
	entries = []
	os.system('clear'); print(divider)
	num = 1
	#get the tag name
	get_tag = "SELECT * FROM tags_list WHERE id ="+str(tag_id)
	tag = query_db(get_tag, current_db_path)[0][1]
	#find zettels under this tag name
	get_ids = "SELECT * FROM tags WHERE tag LIKE '%"+tag+"%' "
	tagged = query_db(get_ids, current_db_path)
	for tagged_entry in tagged:
		found_id = tagged_entry[1]
		get_all_by_tag = "SELECT * FROM main WHERE id =" + str(found_id)
		entry = query_db(get_all_by_tag, current_db_path)[0]
		entries.append(entry)
	for entry in entries:
		print(str(num)+'.', entry[1])
		num += 1
	print(divider); print('zettels under tag', tag, ':', len(entries))

def list_corrupt_links():
	get_all = "SELECT * FROM invalid_links"
	entries = query_db(get_all, current_db_path)
	if entries == []: return False
	same_file = False
	name_previous = ''
	num = 0
	for entry in entries:
		get_file_name = "SELECT * FROM main WHERE id =" + str(entry[1])
		name = query_db(get_file_name, current_db_path)[0][2]
		if name == name_previous: same_file = True
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
	entries = query_db(exec_str, current_db_path)
	if entries == []: return False
	num = 0
	for entry in entries:
		get_file_name = "SELECT * FROM main WHERE id =" + str(entry[1])
		name = query_db(get_file_name, current_db_path)[0][2]
		print(str(num)+'.', 'file:', name)
		num += 1
	return True
	
def list_all_tags():
	str = ''
	print('available tags:')
	for entry in read_tags_list_table():
		str += entry[1] + ', '
	print(str)
	print(divider)

#▒▒▒▒▒▒▒▒▒▒▒▒ SUB-MENU OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def zettel_ops(z_id, z_path):
	os.system('clear'); print_whole_zettel(z_id)
	print_zettel_ops()
	while True:
		print('selected zette:', z_path)
		inp = input("ZETTEL OPS ('?' for commands) » ").strip()
		os.system('clear')
		if inp == "": print_whole_zettel(z_id)
		elif inp == "?": print_zettel_ops()
		elif inp == 'q': return
		
def tag_ops(tag_id, tag):
	os.system('clear')
	print_tag_ops()
	while True:
		print('selected tag:', tag)
		inp = input("TAG OPS ('?' for commands) » ").strip()
		os.system('clear')
		if inp == "": list_by_tag(tag_id)
		elif inp == "?": print_tag_ops()
		elif inp == 'q': return
		
#▒▒▒▒▒▒▒▒▒▒▒▒ MAIN MENU ▒▒▒▒▒▒▒▒▒▒▒▒▒
def import_zettels():
	print(divider); import_to_db(); print(divider)
	
def info():
	print(divider)
	if os.path.isfile(current_db_path):
		print_db_meta(current_db_path); print(divider)
	else: print_no_db(); print(divider)
	
def tree():
	os.system('tree'+' '+path); print(divider)
	print('tree rendred'); print(divider)
	
def make_template():
	gen_template(); print(divider)
	print('generated a non-indexed template zettel:', zettel_template_name)
	print(divider)
	
def review():
	errors = False
	print(divider)
	print('checking your zettels...')
	print(divider); print()
	if not os.path.isfile(current_db_path):
		print_no_db(); print(divider); return
	if list_zettels("SELECT * FROM titleless"):
		print('\nthere are zettels without titles listed above, inspect')
		print(divider); print(); errors = True
	if list_zettels("SELECT * FROM empties"):
		print('\nthere are zettels without text listed above, fill them')
		print(divider); print(); errors = True
	if list_zettels("SELECT * FROM no_links"):
		print('\nthere are unlinked zettels listed above, link them')
		print(divider); errors = True
	if list_zettels("SELECT * FROM self_links"):
		print('\nthere are zettels linking to themselves listed above')
		print(divider); errors = True
	if list_corrupt_links():
		print('\nthere are corrupt links in your zettels, review them')
		print(divider); errors = True
	if not errors:
		print('all good, no corrupt links or unlinked zettels')
		print(divider)
	
def make_test_zettels():
	if make_test_batch(): print_made_tests()
	
def main_menu():
	os.system('clear')
	print_main_ops()
	while True:
		inp = input("MAIN MENU ('?' for commands) » ").strip()
		os.system('clear')
		if inp == "": info()
		elif inp == "n": make_new_zettel()
		elif inp == "f": search_zettel('name')
		elif inp == "ft": search_zettel('tag')
		elif inp == "r": review()
		elif inp == "tree": tree()
		elif inp == "init": init_new_db()
		elif inp == "temp": make_template()
		elif inp == "test": make_test_zettels()
		elif inp == "import": import_zettels()
		elif inp == "t": git_menu()
		elif inp == "?": print_main_ops()
		elif inp == "q": quit()

#▒▒▒▒▒▒▒▒▒▒▒▒ PRINT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def print_zettel_ops():
	print(divider)
	print('() - read current zettel')
	print('(q) - return to previous menu')
	print(divider)
	
def print_tag_ops():
	print(divider)
	print('() - show zettels under this tag')
	print('(q) - return to previous menu')
	print(divider)
	
def print_search_commands():
	print("'number' - select entry")
	print("(c) - clear search query and start again")
	print("(q) - stop searching and return")
	print(divider)

def print_searching():
	print('keep narrowing your search by entering more characters')
	print("or enter ':' for search tools")
	print(divider)
	
def print_made_tests():
	print(divider)
	print('generated a number of test zettels')
	print("don't forget to import them into the database")
	print(divider)
	
def print_test_failed():
	print(divider)
	print('make sure you enter numbers')
	print(divider)

def print_test_warn():
	print(divider)
	print('make sure you have backed up your journal folder')
	print('this will generate a batch of zettel .md cards in it')
	print('you will have to import them back into a database')
	print(divider)

def print_links_select():
	print(divider)
	print('select a zettel from the list to link to')
	print('you can open and read it as usual')
	print('to confirm selection return after finding it')
	print(divider)

def print_tags_select():
	print(divider)
	print('select a suitable tag for your zettel')
	print('you can either search for existing tag')
	print('or write a new one if no suitable found')
	print(divider)

def print_no_db():
	print('no database matching the name provided in this script')
	print('check the name in the script header, or import or')
	print('initiate the database via respective commands')
	
def print_main_ops():
	print(divider)
	print('() - show statistics')
	print('(f) - incrementally find zettel to enter the database')
	print('(ft) - find zettel by tag to enter the database')
	print('(r) - review zettels for errors in links and content')
	print('(n) - start writing a new zettel')
	print('(tree) - use "tree" command to show files')
	print('(init) - make a new database (name in script header)')
	print('(temp) - generate a template zettel')
	print('(test) - generate a batch of test zettels')
	print('(import) - import .md zettels to the database')
	print('(t) - git menu')
	print('(q) - quit')
	print(divider)

def print_git_ops():
	print(divider)
	print('() - current')
	print('(l) - log')
	print('(s) - status')
	print('(a) - add')
	print('(c) - commit')
	print('(p) - push')
	print('(r) - revert')
	print('(ha) - hard reset')
	print('(u) - launch "gitui" (must be installed)')
	print('(q) - quit to main')
	print(divider)

def print_writer_options():
	print(divider)
	print('to use any of provided external editors,')
	print('make sure they are installed\n')
	print('() - write with user-defined editor (see script header)')
	print('(v) - write using vim')
	print('(e) - write using emacs')
	print('(n) - write using nano')
	print(divider)
	
def print_db_meta(db_path):
	try:
		meta = query_db("SELECT * FROM meta", db_path)
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
	except:
		print("couldn't find metadata table on:", db_path)

def print_whole_zettel(z_id):
	print(divider)
	print(read_whole_zettel(z_id))
	print(divider)

#▒▒▒▒▒▒▒▒▒▒▒▒ START ▒▒▒▒▒▒▒▒▒▒▒▒▒
main_menu()


