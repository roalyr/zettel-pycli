#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
database_name = "my_vault" # default name for new databases
default_editor = "nano" # enter anything that suits your preference
sort_tags = True # if true - sorts alphabetically
sort_titles = False # if true - sorts alphabetically
draw_tags_in_line = True # if false - print tags in column
draw_titles_in_line = False # if false - print titles in column

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


#▒▒▒▒▒▒▒▒▒▒▒▒ CONSTANTS ▒▒▒▒▒▒▒▒▒▒▒▒▒
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

#▒▒▒▒▒▒▒▒▒▒▒▒ SQL SCHEMAS ▒▒▒▒▒▒▒▒▒▒▒▒▒
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
		z_id_from integer NOT NULL, z_id_to integer NOT NULL
	); '''
create_invalid_links_table = '''
	CREATE TABLE IF NOT EXISTS invalid_links (
		id integer PRIMARY KEY,
		z_id_from integer NOT NULL, link_name text NOT NULL
	); '''
create_no_links_table = '''
	CREATE TABLE IF NOT EXISTS no_links (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_self_links_table = '''
	CREATE TABLE IF NOT EXISTS self_links (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_no_bodies_table = '''
	CREATE TABLE IF NOT EXISTS no_bodies (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_no_titles_table = '''
	CREATE TABLE IF NOT EXISTS no_titles (
		id integer PRIMARY KEY, z_id_from integer NOT NULL
	); '''
create_tags_table = '''
	CREATE TABLE IF NOT EXISTS tags (
		id integer PRIMARY KEY, z_id integer NOT NULL, tag text NOT NULL
	); '''
create_taglist_table = '''
	CREATE TABLE IF NOT EXISTS taglist (
		id integer PRIMARY KEY, tag text NOT NULL, UNIQUE ( tag )
	); '''

insert_main = '''INSERT INTO main ( z_title, z_path, z_body ) VALUES ( ?, ?, ? ) '''
insert_links = '''INSERT INTO links ( z_id_from, z_id_to ) VALUES ( ?, ? ) '''
insert_invalid_links = '''INSERT INTO invalid_links ( z_id_from, link_name ) VALUES ( ?, ? ) '''
insert_self_links = '''INSERT INTO self_links ( z_id_from ) VALUES ( ? ) '''
insert_no_links = '''INSERT INTO no_links ( z_id_from ) VALUES ( ? ) '''
insert_no_bodies = '''INSERT INTO no_bodies ( z_id_from ) VALUES ( ? ) '''
insert_no_titles = '''INSERT INTO no_titles ( z_id_from ) VALUES ( ? ) '''
insert_tags = '''INSERT INTO tags ( z_id, tag ) VALUES ( ?, ? ) '''
insert_taglist = '''INSERT OR IGNORE INTO taglist ( tag ) VALUES ( ? ) ''' 
insert_meta = '''
	INSERT INTO meta (
		db_name, datetime, tot_zettels, tot_links, tot_invalid_links,
		tot_no_links, tot_self_links, tot_no_bodies, tot_no_titles
	) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? ) ''' #add tags num
	
update_z_body = 'UPDATE main SET z_body = ? WHERE id = ?'
update_z_title = 'UPDATE main SET z_title = ? WHERE id = ?'

from_main_id = "SELECT * FROM main WHERE id = ?"
from_main_z_path = "SELECT * FROM main WHERE z_path = ?"
from_main_all = "SELECT * FROM main"
from_main_z_title_like = "SELECT * FROM main WHERE z_title LIKE ? "
from_main_z_body_like = "SELECT * FROM main WHERE z_body LIKE ? "
from_main_z_path_like = "SELECT * FROM main WHERE z_path LIKE ? "

from_invalid_links_all = "SELECT * FROM invalid_links"
from_self_links_all = "SELECT * FROM self_links"
from_no_links_all = "SELECT * FROM no_links"
from_no_bodies_all = "SELECT * FROM no_bodies"
from_no_titles_all = "SELECT * FROM no_titles"

from_taglist_id = "SELECT * FROM taglist WHERE id = ?"
from_taglist_all = "SELECT * FROM taglist"
from_taglist_tag_like = "SELECT * FROM taglist WHERE tag LIKE ? "

from_tags_z_id = "SELECT * FROM tags WHERE z_id = ?"
from_tags_all_dist = "SELECT DISTINCT * FROM tags"
from_tags_tag_like = "SELECT * FROM tags WHERE tag LIKE ? "

from_links_z_id_from = "SELECT * FROM links WHERE z_id_from = ?"
from_links_z_id_to = "SELECT * FROM links WHERE z_id_to = ?"

delete_taglist_all = "DELETE FROM taglist"
delete_links_z_id_from = "DELETE FROM links WHERE z_id_from = ?"
delete_links_z_id_to = "DELETE FROM links WHERE z_id_to = ?"

#▒▒▒▒▒▒▒▒▒▒▒▒ WRITING DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def write_zettel(z_title, z_path, z_body):
	z_id = add_to_db([z_title, z_path, z_body], insert_main, current_db_path)
	return z_id #regurns only last id

def write_z_tags(z_id, tags):
	entry_list = []
	for tag in tags: #swap tag ID with z_id
		entry_list.append((z_id, tag[1]))
	incr_add_to_db(entry_list, insert_tags, current_db_path)

def write_new_tag_to_list(tags):
	t_id = incr_add_to_db(tags, insert_taglist, current_db_path)
	return t_id #regurns only last id
	
def write_z_links(z_id, links):
	entry_list = []
	for link in links: #swaps tag ID with z_id
		entry_list.append((z_id, link[0]))
	incr_add_to_db(entry_list, insert_links, current_db_path)
	
#▒▒▒▒▒▒▒▒▒▒▒▒ READING DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def read_whole_zettel(z_id):
	try: 
		title = read_main_id(z_id)[1]
		body = read_main_id(z_id)[3]
	except IndexError: title =''; body =''
	tags = str(read_tags_z_id(z_id)) 
	links_from = str(read_links_z_id_from(z_id))
	return marker_title + '\n' + title + '\n\n' \
	+ marker_body+ '\n' + body + '\n\n' \
	+ marker_tags+ '\n' + tags + '\n\n' \
	+ marker_links+ '\n' + links_from

def read_links_z_id_from(z_id): return query_db(z_id, from_links_z_id_from, current_db_path)
def read_links_z_id_to(z_id): return query_db(z_id, from_links_z_id_to, current_db_path)

def read_invalid_links_all(): return query_db(None, from_invalid_links_all, current_db_path)

def read_taglist_id(id): return query_db(id, from_taglist_id, current_db_path)
def read_taglist_all(): return query_db(None, from_taglist_all, current_db_path)
def read_taglist_tags_like(name): return query_db('%'+name+'%', from_taglist_tag_like, current_db_path)

def read_tags_all_dist(): return query_db(None, from_tags_all_dist, current_db_path)
def read_tags_z_id(z_id): return query_db(z_id, from_tags_z_id, current_db_path)
def read_tags_tag_like(name): return query_db('%'+name+'%', from_tags_tag_like, current_db_path)

def read_main_id(id): return query_db(id, from_main_id, current_db_path)
def read_main_z_path(name): return query_db(name, from_main_z_path, current_db_path)
def read_main_all(): return query_db(None, from_main_all, current_db_path)
def read_main_z_titles_like(name): return query_db('%'+name+'%', from_main_z_title_like, current_db_path)
def read_main_z_path_like(name): return query_db('%'+name+'%', from_main_z_path_like, current_db_path)
def read_main_z_body_like(name): return query_db('%'+name+'%', from_main_z_body_like, current_db_path)

#▒▒▒▒▒▒▒▒▒▒▒▒ REWRITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
#called by 'edit' functions
def rewrite_z_body(id, text):
	add_to_db([text, id], update_z_body, current_db_path)
	
def rewrite_z_title(id, title):
	add_to_db([title, id], update_z_title, current_db_path)

#▒▒▒▒▒▒▒▒▒▒▒▒ REMOVE / REBUILD OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def rescan_tags_to_list(): #after tag edit
	tags = []
	delete_from_db(None, delete_taglist_all, current_db_path)
	for entry in read_tags_all_dist():
		tags.append((entry[2],)) #need only names
	incr_add_to_db(tags, insert_taglist, current_db_path)
	
def rescan_meta(): #after any edit
	print()
	
def remove_links_from(z_id): #after zettel removal, or optional
	links = read_links_z_id_from(z_id)
	print(links)
	
def remove_links_to(z_id): #after zettel removal, or optional
	links = read_links_z_id_to(z_id)
	print(links)
	
#▒▒▒▒▒▒▒▒▒▒▒▒ DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def import_zettels():
	#str?
	import_to_db();
	
def delete_from_db(query, exec_line, db_path):
	conn = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				if query: 
					c.execute(exec_line, (query,))
				else: 
					c.execute(exec_line)
			except Error as e: print(e)
			conn.commit(); conn.close();
	
def query_db(query, exec_line, db_path):
	found = []; conn = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				if query: 
					c.execute(exec_line, (query,))
				else: 
					c.execute(exec_line)
				found = c.fetchall()
			except Error as e: print(e)
			conn.close(); return found
			
def add_to_db(entry, exec_line, db_path):
	conn = None; id = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				if len(entry) == 1: c.execute(exec_line, (entry[0],))
				elif len(entry) == 2: c.execute(exec_line, (entry[0], entry[1],))
				elif len(entry) == 3: c.execute(exec_line, (entry[0], entry[1], entry[2],))
				else: 
					print('Attempted to write', len(entry), 'fields, which is not supported')
					print('The SQLite command is:', exec_line)
					quit()
			except Error as e: print(e)
			conn.commit()
			id = c.lastrowid
			conn.close();
			return id
			
def incr_add_to_db(entry_list, exec_line, db_path):
	conn = None; id = None
	try: conn = sqlite3.connect(db_path)
	except Error as e: print(e)
	finally:
		if conn:
			try:
				c = conn.cursor()
				for entry in entry_list:
					if len(entry) == 1: c.execute(exec_line, (entry[0],))
					elif len(entry) == 2: c.execute(exec_line, (entry[0], entry[1],))
					elif len(entry) == 3: c.execute(exec_line, (entry[0], entry[1], entry[2],))
					else: 
						print('Attempted to write', len(entry), 'fields, which is not supported')
						print('The SQLite command is:', exec_line)
						quit()
			except Error as e: print(e)
			conn.commit()
			id = c.lastrowid
			conn.close();
			return id

def import_to_db():
	print('folders with nested sub-folders are not supported')
	inp = s_prompt('local folder name')
	if not os.path.isdir(inp):
		print('wrong folder name, aborting'); return #failed
	dt_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
	dt_str_file = time.strftime("%d%b%Y%H%M%S", time.localtime())
	db_name_imported = os.path.join('imported_' + inp + '_' + dt_str_file + '.db')
	#db_name_imported = current_db_path
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
				c.execute(create_tags_table); c.execute(create_no_bodies_table)
				c.execute(create_no_titles_table); c.execute(create_taglist_table);
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
						c.execute(from_main_z_path, (z_path,))
						current_zettel_id = c.fetchall()[0][0]
						#store metadata
						for tag in tags:
							c.execute(insert_tags, (current_zettel_id, tag,))
							c.execute(insert_taglist, (tag,))
						#store errors
						if z_body == '':
							c.execute(insert_no_bodies, (current_zettel_id,))
							tot_no_bodies += 1
						if z_title == '':
							c.execute(insert_no_titles, (current_zettel_id,))
							tot_no_titles += 1
				#links must be done only once main tabe is populated
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name: continue #skip it
						full_path = os.path.join(root, name)
						parsed = parse_zettel_metadata(full_path)
						z_path = name
						links = parsed['links']
						tot_links += len(links)
						#get the current zettel id
						c.execute(from_main_z_path, (z_path,))
						current_zettel_id = c.fetchall()[0][0]
						#see if links point out to existing nodes
						for link_path in links:
							#destination zettel
							c.execute(from_main_z_path, (link_path,))
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
								c.execute(insert_invalid_links, (current_zettel_id, link_path,))
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
				print_db_meta(db_name_imported)
				
				print('to use the database rename it to match:', database_name+'.db')
			except Error as e: print(e)
			conn.close()
			
def init_new_db():
	#check and abort
	if os.path.isfile(current_db_path): print_db_exists(); return
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
				c.execute(create_tags_table); c.execute(create_no_bodies_table)
				c.execute(create_no_titles_table); c.execute(create_taglist_table);
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
	while z_title == '': z_title = c_prompt('enter zettel title')
	while z_body == '':
		print_writer_options()
		inp = c_prompt('')
		if inp == '': z_body = write_ext(default_editor)
		elif inp == 'v': z_body = write_ext('vim')
		elif inp == 'n': z_body = write_ext('nano')
		elif inp == 'e': z_body = write_ext('emacs')
		elif inp == "q": return
	
	#links
	while True:
		z_links = [] 
		
		print_links_select()
		while True: #guard
			print_writing_links()
			inp = c_prompt('review your links')
			
			if inp == '': 
				try: z_links += search_zettels()
				except NoneType: pass
			elif inp == "r" or inp == "p": break
		if inp == "r": continue
		elif inp == "p": break
	#tags
	while True:
		z_tags = [] 
		
		print_tags_select()
		while True: #guard
			print_writing_tags()
			inp = c_prompt('review your tags')
			
			if inp == '': 
				try: z_tags += search_tags()
				except NoneType: pass
			elif inp == "r" or inp == "p": break
		if inp == "r": continue
		elif inp == "p": break
	#generate filename for export feature
	path_length = 30
	z_path = z_title
	if len(z_path) > path_length: z_path = z_path[0:path_length]
	z_path = z_path.strip().replace(' ', '_')
	z_path = re.sub(r'(?u)[^-\w.]', '_', z_path) 
	z_path += '.md'
	z_id = write_zettel(z_title, z_path, z_body)
	write_z_tags(z_id, z_tags)
	write_z_links(z_id, z_links)
	#update meta
	
	
	print('Filename:',z_path)
	print('Zettel id:',z_id)
	
	print('Title:',z_title)
	print()
	print('Text:', z_body)
	print()
	print('Tags:', str_from_list(sort_tags, draw_tags_in_line, z_tags, 1))
	print()
	print('Links:', str_from_list(sort_tags, draw_tags_in_line, z_links, 1))
	print('Links ids:', str_from_list(sort_tags, draw_tags_in_line, z_links, 0))
	

def make_new_tag():
	
	tag = ''; conf = ''
	while tag =='':
		tag = s_prompt('write a new tag')
	while conf =='':
		
		print('New tag:', tag)
		conf = c_prompt('is this correct?')
	
	t_id = write_new_tag_to_list([(tag,)])
	return (t_id, tag)

#▒▒▒▒▒▒▒▒▒▒▒▒ SEARCH OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def search_zettels():
	flag = ''
	while True:
		print_how_to_search_zettel()
		inp = inp = c_prompt('')
		if inp == 'n': flag = 'name'; break
		if inp == 't': flag = 'tag'; break
		if inp == 'q': return
	entries = []
	while True:
		s = find_zettel(flag)
		if s['found'] or s['stop']: 
			
			if s['found']: entries.append(s['found'])
			if s['stop']: break
			inp = inp = c_prompt('search for more?')
			if inp == 'q': break
	entries = list(dict.fromkeys(entries)) #dedup
	list_selected_zettels(entries)
	return entries
	
def search_tags():
	entries = []
	while True:
		s = find_tags()
		if s['found'] or s['stop']: 
			
			if s['found']: entries.append(s['found'])
			if s['stop']: break
			inp = inp = c_prompt('search for more?')
			if inp == 'q': break
	entries = list(dict.fromkeys(entries)) #dedup
	list_selected_tags(entries)
	return entries
	
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
	
def print_many_zettels_or_return(entries):
	num = 1
	if len(entries) > 1:
		for entry in entries:
			print(str(num)+'.', entry[1])
			num += 1
		print('total search hits:', len(entries)); print_searching()
	elif len(entries) == 0: 
		print("no zettel found, ':' for options");
	elif len(entries) == 1: 
		print_found_zettels(entries[0], '')
		return entries[0] #return what was found by narrowing down
		
def print_many_tags_or_return(entries):
	num = 1
	if len(entries) > 1:
		for entry in entries:
			print(str(num)+'.', entry[1])
			num += 1
		print('total search hits:', len(entries)); print_searching()
	elif len(entries) == 0: 
		print("no tags found, ':' for options");
	elif len(entries) == 1: 
		print_found_tags(entries[0], '')
		return entries[0] #return what was found by narrowing down

def zettel_sub_menu(s):
	print_search_zettel_commands()
	inp = c_prompt('ZETTEL search')
	try: 
		print_found_zettels(s['entries'][int(inp)-1], int(inp))
		s['found'] = s['entries'][int(inp)-1]
	except ValueError: pass
	finally:
		if inp == "c": s['name'] = ''; s['inp'] = ''; s['entries'] = read_main_all() #reset
		if inp == "q": s['stop'] = True
	return s
	
def tag_sub_menu(s):
	print_search_tag_commands()
	inp = c_prompt('TAG search')
	try: 
		print_found_tags(s['entries'][int(inp)-1], int(inp))
		s['found'] = s['entries'][int(inp)-1]
	except ValueError: pass
	finally:
		if inp == "c": s['name'] = ''; s['inp'] = ''; s['entries'] = read_taglist_all() #reset
		elif inp == "q": s['stop'] = True
		elif inp == "n": s['found'] = make_new_tag()
	return s

def find_zettel(flag):
	s = {'found': None, 'name': '', 'inp': '', 'entries': [], 'stop': False}
	s['entries'] = read_main_all()
	while True:
		
		if s['inp'] != ':': s['name'] += s['inp']
		if flag == 'tag': list_all_tags()
		if flag == 'name': s['entries'] = read_main_z_titles_like(s['name'])
		elif flag == 'tag':
			s['entries'].clear() #reset
			if s['name'] != '': #if entereg something - fing by tag
				tagged = read_tags_tag_like(s['name'])
				for tagged_entry in tagged:
					found_id = tagged_entry[1]
					entry = read_main_id(found_id)[0]
					s['entries'].append(entry)
				s['entries'] = list(dict.fromkeys(s['entries'])) #dedup
			else: s['entries'] = read_main_all() #or show all
		s['found'] = print_many_zettels_or_return(s['entries'])
		if s['inp'] == ':': 
			s = zettel_sub_menu(s); 
			
			if not s['stop']:
				if flag == 'tag': list_all_tags()
				print_many_zettels_or_return(s['entries']); 
		if s['found'] or s['stop']: return s
		s['inp'] = s_prompt('searching zettel by ' + flag +': '+ s['name'])
		
def find_tags():
	s = {'found': None, 'name': '', 'inp': '', 'entries': [], 'stop': False}
	s['entries'] = read_taglist_all()
	while True:
		
		if s['inp'] != ':': s['name'] += s['inp']
		s['entries'] = read_taglist_tags_like(s['name'])

		s['found'] = print_many_tags_or_return(s['entries'])
		if s['inp'] == ':': 
			s = tag_sub_menu(s); 
			
			if not s['stop']:
				print_many_tags_or_return(s['entries']); 
		if s['found'] or s['stop']: return s
		s['inp'] = s_prompt('searching existing tag: '+ s['name'])

#▒▒▒▒▒▒▒▒▒▒▒▒ LIST OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def list_by_tag(tag_id):
	list_names = []; list_zettel_entries = []
	num = 1
	tag_entries = read_taglist_id(tag_id)
	tag = tag_entries[0][1]
	tagged_entries = read_tags_tag_like(tag)
	for tagged_entry in tagged_entries:
		found_id = tagged_entry[1]
		zettel_entries = read_main_id(found_id)
		list_zettel_entries.append(zettel_entries[0]) #read always returns a list
		z_title = zettel_entries[0][1]
		list_names.append(z_title)
	for entry in list_names:
		print(str(num)+'.', entry)
		num += 1
	print('zettels under tag:', tag, '-', len(list_names))
	return list_zettel_entries

def list_invalid_links():
	entries = read_invalid_links_all()
	if entries == []: return False
	same_zettel = False; id_prev = None; num = 1
	for entry in entries:
		zettel = read_main_id(entry[1])
		z_title = zettel[0][1]; 
		z_id = zettel[0][0]; 
		invalid_link_name = entry[2]
		if z_id == id_prev: same_zettel = True
		if same_zettel:
			print('   └─', invalid_link_name)
			same_zettel = False
		else:
			print()
			print(str(num)+'.', 'id:', str(z_id) + ',', z_title)
			print('   corrupt links:')
			print('   └─', invalid_link_name)
			num += 1
		id_prev = z_id
	return True
		
def list_zettels(query, exec_str): #for other errors
	entries = query_db(query, exec_str, current_db_path); num = 1
	if entries == []: return False;
	for entry in entries:
		z_id = entry[1]; z_title = read_main_id(z_id)[0][1]
		print(str(num)+'.', 'id:', str(z_id) + ',', z_title)
		num += 1
	return True
	
def str_from_list(sort_flag, draw_flag, init, i):
	strn = ''; fin = [];
	for entry in init: fin.append(entry[i])
	if sort_flag: fin.sort()
	if draw_flag:
		for entry in fin: strn += str(entry) + ', '
	else:
		for entry in fin: strn += str(entry) + '\n'
	return strn
	
def list_all_tags():
	strn = str_from_list(sort_tags, draw_tags_in_line, read_taglist_all(), 1)
	print('available tags:'); print(strn);

def list_selected_zettels(entries):
	strn = str_from_list(sort_titles, draw_titles_in_line, entries, 1)
	print('viewed / selected zettels:'); print(strn)
	
def list_selected_tags(entries):
	strn = str_from_list(sort_tags, draw_tags_in_line, entries, 1)
	print('viewed / selected tags:'); print(strn);

#▒▒▒▒▒▒▒▒▒▒▒▒ ANALYZE OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def info():
	if os.path.isfile(current_db_path):
		print_db_meta(current_db_path)
	else: print_no_db()
	
def tree():
	#str
	os.system('tree'+' '+path)
	
def review():
	print_start_check(); errors = False
	if not os.path.isfile(current_db_path): print_no_db(); return
	if list_zettels(None, from_no_titles_all): print_no_titles(); errors = True
	if list_zettels(None, from_no_bodies_all): print_no_bodies(); errors = True
	if list_zettels(None, from_no_links_all): print_no_links(); errors = True
	if list_zettels(None, from_self_links_all): print_self_links(); errors = True
	if list_invalid_links(): print_invalid_links(); errors = True
	if not errors: print_check_passed()

#▒▒▒▒▒▒▒▒▒▒▒▒ GIT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def git_info():
	print('Current head:');
	os.system("git log --branches --oneline -n 1")
	
def git_status():
	os.system("git status")
	
def git_log_f(): 
	os.system("git log --branches --oneline -n 20"); 
	
def git_add():
	os.system("git add . ")
	os.system("git status --short")
	
def git_launch_gitui():
	os.system('gitui')

def git_push():
	os.system("git push --all")

def git_commit_f():
	print('Files added:'); 
	git_add(); git_info()
	commit_name = c_prompt("commit name (' ' to abort)")
	if commit_name =='': return
	inp = c_prompt("really? ('yes' to proceed)")
	if inp == "yes": os.system("git commit -m "+ commit_name)
	
def git_revert_f():
	print('Commits:');
	git_log_f()
	commit_name = c_prompt("commit name to revert (' ' to abort)")
	if commit_name =='': return
	os.system("git revert "+ commit_name)
	
def git_reset_hard_f():
	print('Commits:');
	git_log_f()
	commit_name = c_prompt("commit name to reset (' ' to abort)")
	if commit_name =='': return
	inp = c_prompt("really? ('yes' to proceed)")
	if inp == "yes": os.system("git reset --hard "+ commit_name)

#▒▒▒▒▒▒▒▒▒▒▒▒ FILE & TEST OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def make_template():
	gen_template();
	print('generated a non-indexed template zettel:', zettel_template_name)
	
def make_test_zettels():
	if make_test_batch(): print_made_tests()

def gen_template():
	f = open(path + "/" + zettel_template_name, "w")
	f.write(zettel_template)
	f.close()
	
def make_test_batch():
	
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

	print_test_warn()
	try:
		inp_num = int(s_prompt('how many zettels to make?'))
		inp_links = int(s_prompt('how many links per zettel'))
		inp_corr = float(s_prompt('amount of correct zettels (0.0..1.0)'))
	except: print_test_wrong_input(); return False #failed
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
			except ValueError: pass
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
			except ValueError: pass
			
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

#▒▒▒▒▒▒▒▒▒▒▒▒ MENU OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def git_menu():
	print_git_ops()
	while True:
		inp = c_prompt('GIT')
		print_git_ops()
		if inp == "": git_info()
		elif inp == "l": git_log_f()
		elif inp == "s": git_status()
		elif inp == "a": git_add()
		elif inp == "c": git_commit_f()
		elif inp == "p": git_push()
		elif inp == "r": git_revert_f()
		elif inp == "ha": git_reset_hard_f()
		elif inp == "u": git_launch_gitui()
		elif inp == "q": break
		
def zettel_ops(z_id, z_path):
	print_zettel_ops()
	while True:
		inp = c_prompt('ZETTEL')
		print_whole_zettel(z_id); print_zettel_ops()
		if inp == 'q': return
		
def tag_ops(tag_id, tag):
	zettel_entries = list_by_tag(tag_id); print_tag_ops()
	while True:
		inp = c_prompt('TAG')
		zettel_entries = list_by_tag(tag_id); print_tag_ops()
		if inp == 'q': return

def main_menu():
	print_main_ops()
	while True:
		inp = c_prompt('MENU')
		print_main_ops()
		if inp == "i": info();
		elif inp == "n": make_new_zettel(); print_main_ops()
		elif inp == "z": search_zettels(); print_main_ops()
		elif inp == "t": search_tags(); print_main_ops()
		elif inp == "r": review()
		elif inp == "tree": tree()
		elif inp == "init": init_new_db(); print_main_ops()
		elif inp == "temp": make_template(); print_main_ops()
		elif inp == "test": make_test_zettels(); print_main_ops()
		elif inp == "import": import_zettels(); print_main_ops()
		elif inp == "git": git_menu(); print_main_ops()
		elif inp == "q": quit()

#▒▒▒▒▒▒▒▒▒▒▒▒ PRINT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
#DB ERROR CHECK
def print_start_check():
	cl_divider()
	print('starting to check the database')
	divider()
	
def print_no_db():
	cl_divider()
	print('no database matching the name provided in this script')
	print('check the name in the script header, or import or')
	print('initiate the database via respective commands')
	divider()
	
def print_no_titles():
	print()
	print('there are zettels without titles listed above, inspect')
	divider()

def print_no_bodies():
	print()
	print('there are zettels without text listed above, fill them')
	divider()
	
def print_no_links():
	print()
	print('there are unlinked zettels listed above, link them')
	divider()
	
def print_self_links():
	print()
	print('there are zettels linking to themselves listed above')
	divider()
	
def print_invalid_links():
	print()
	print('there are corrupt links in your zettels, review them')

def print_check_passed():
	divider()
	print('all good, no corrupt links or unlinked zettels')

#DB
def print_db_exists():
	cl_divider()
	print('a database like this already exists, aborting')

#TEST
def print_test_warn():
	cl_divider()
	print('make sure you have backed up your journal folder')
	print('this will generate a batch of zettel .md cards in it')
	print('you will have to import them back into a database')
	
def print_test_wrong_input():
	cl_divider()
	print('make sure you enter numbers')

def print_made_tests():
	cl_divider()
	print('generated a number of test zettels')
	print("don't forget to import them into the database")

#WRITING ZETTEL
def print_links_select():
	cl_divider()
	print('select zettels that you want to LINK to')

def print_tags_select():
	cl_divider()
	print('select a suitable TAG for your zettel')
	print('you can either search for existing tag')
	print('or write a new one if no suitable found')
	
def print_writing_links():
	divider()
	print('() - start selecting links')
	print('(p) - proceed to next step')
	print('(r) - redo (start selecting anew)')
	
def print_writing_tags():
	divider()
	print('() - start selecting tags')
	print('(p) - proceed to next step')
	print('(r) - redo (start selecting anew)')

#MAIN MENU
def print_main_ops():
	cl_divider()
	print('(i) - show statistics')
	print('(z) - find zettel by name to enter the database')
	print('(t) - browse tags in the database')
	print('(r) - review zettels for errors in links and content')
	print('(n) - start writing a new zettel')
	print('(tree) - use "tree" command to show files')
	print('(init) - make a new database (name in script header)')
	print('(temp) - generate a template zettel')
	print('(test) - generate a batch of test zettels')
	print('(import) - import .md zettels to the database')
	print('(git) - git menu')
	print('(q) - quit')

#GIT MENU
def print_git_ops():
	cl_divider()
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

#SELECTING WRITER
def print_writer_options():
	cl_divider()
	print('to use any of provided external editors,')
	print('make sure they are installed\n')
	print('() - write with user-defined editor (see script header)')
	print('(v) - write using vim')
	print('(e) - write using emacs')
	print('(n) - write using nano')
	
#SEARCHING
def print_searching():
	divider()
	print('keep narrowing your search by entering more characters')
	print("or enter ':' for search tools")
	
#SEARCHING ZETTEL
def print_how_to_search_zettel():
	cl_divider()
	print('how do you want to find a zettel?')
	divider()
	print('(n) - by zettel name (title)')
	print('(t) - by tag')
	print('(q) - to return')

def print_search_zettel_commands():
	divider()
	print('zettel search commands')
	divider()
	print("'number' - select entry")
	print("(c) - clear search query and start again")
	print("(q) - stop searching and return")

def print_zettel_ops():
	divider()
	print('(q) - return to previous menu (confirms selection)')
	
#SEARCHING TAGS
def print_search_tag_commands():
	divider()
	print('tag search commands')
	divider()
	print("'number' - select entry")
	print('(n) - add a new tag not from list')
	print("(c) - clear search query and start again")
	print("(q) - stop searching and return")
	
def print_tag_ops():
	divider()
	print('(q) - return to previous menu (confirms selection)')
	 
#▒▒▒▒▒▒▒▒▒▒▒▒ OTHER PRINTING ▒▒▒▒▒▒▒▒▒▒▒▒▒
def print_db_meta(db_path):
	try:
		cl_divider()
		meta = query_db(None, "SELECT * FROM meta", db_path)
		print('database name:', meta[0][1])
		print('created:', meta[0][2])
		print('total number of zettels:', meta[0][3])
		print('total number of links:', meta[0][4])
		divider()
		print('warnings:')
		print('invalid links:', meta[0][5])
		print('zettels without links:', meta[0][6])
		print('zettels that link to themselves:', meta[0][7])
		print('empty zettels:', meta[0][8])
		print('zettels without titles:', meta[0][9])
	except:
		divider()
		print("couldn't find metadata table on:", db_path)
		print('check if database exists')

def print_whole_zettel(z_id):
	cl_divider()
	print(read_whole_zettel(z_id))

#▒▒▒▒▒▒▒▒▒▒▒▒ PROMPTS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def c_prompt(prompt): divider(); return input(prompt+" » ").strip()
def s_prompt(prompt): divider(); return input(prompt+" « ").strip()

#▒▒▒▒▒▒▒▒▒▒▒▒ CLEAR SCREEN AND DIVIDER ▒▒▒▒▒▒▒▒▒▒▒▒▒
def divider(): 
	d_line = '-------------------------------------------------------'
	print(d_line)
def cl(): os.system('cls' if os.name == 'nt' else 'clear')
def cl_divider(): cl(); divider()
	
#▒▒▒▒▒▒▒▒▒▒▒▒ START ▒▒▒▒▒▒▒▒▒▒▒▒▒
main_menu()


