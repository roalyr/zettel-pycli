#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
database_name = "my_vault" # default name for new databases
default_editor = "python" # a text editor command to call by default
# use "python" to disable prompt and always use native input
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
import os, fnmatch, shutil, pathlib, sqlite3, time, re, random, tempfile, subprocess, py_compile
from sqlite3 import Error

path = os.path.join(os.getcwd(), database_name)
current_db_path = os.path.join(os.getcwd(), database_name + '.db')
zettel_template_name = "_template.md"

marker_title = '[TITLE]'
marker_tags = '[TAGS]'
marker_links = '[ZETTEL LINKS]'
marker_body = '[BODY]'
sub_menu_depth = 0 #allows or forbids cyclical sub-menus

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

#INSTERT
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

#SELECT
select_main_id = "SELECT * FROM main WHERE id = ?"
select_main_z_path = "SELECT * FROM main WHERE z_path = ?"
select_main_all = "SELECT * FROM main"
select_main_z_title_like = "SELECT * FROM main WHERE z_title LIKE ? "
select_main_z_body_like = "SELECT * FROM main WHERE z_body LIKE ? "
select_main_z_path_like = "SELECT * FROM main WHERE z_path LIKE ? "

select_invalid_links_all = "SELECT * FROM invalid_links"
select_self_links_all = "SELECT * FROM self_links"
select_no_links_all = "SELECT * FROM no_links"
select_no_bodies_all = "SELECT * FROM no_bodies"
select_no_titles_all = "SELECT * FROM no_titles"

select_taglist_id = "SELECT * FROM taglist WHERE id = ?"
select_taglist_all = "SELECT * FROM taglist"
select_taglist_tag_like = "SELECT * FROM taglist WHERE tag LIKE ? "

select_tags_z_id = "SELECT * FROM tags WHERE z_id = ?"
select_tags_all_dist = "SELECT DISTINCT * FROM tags"
select_tags_tag_like = "SELECT * FROM tags WHERE tag LIKE ? "

select_links_z_id_from = "SELECT * FROM links WHERE z_id_from = ?"
select_links_z_id_to = "SELECT * FROM links WHERE z_id_to = ?"

#UPDATE
update_main_z_body = 'UPDATE main SET z_body = ? WHERE id = ?'
update_main_z_title = 'UPDATE main SET z_title = ? WHERE id = ?'

update_tags_tag = 'UPDATE tags SET tag = ? WHERE tag = ?'

#DELETE
delete_taglist_all = "DELETE FROM taglist"

delete_invalid_links_all = "DELETE FROM invalid_links"

delete_tags_z_id = "DELETE FROM tags WHERE z_id = ?"
delete_tags_tag = "DELETE FROM tags WHERE tag = ?"

delete_links_z_id_from = "DELETE FROM links WHERE z_id_from = ?"
delete_links_z_id_to = "DELETE FROM links WHERE z_id_to = ?"

#▒▒▒▒▒▒▒▒▒▒▒▒ WRITING DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def write_zettel(z_title, z_path, z_body):
	z_id = add_to_db([z_title, z_path, z_body], insert_main, current_db_path)
	return z_id #regurns only last id

def write_tags(z_id, tags):
	entry_list = []
	for tag in tags: #swap tag ID with z_id
		entry_list.append((z_id, tag[1]))
	incr_add_to_db(entry_list, insert_tags, current_db_path)

def write_taglist_tag(tags):
	t_id = incr_add_to_db(tags, insert_taglist, current_db_path)
	return t_id #regurns only last id
	
def write_links_from(z_id, zettels):
	entry_list = []
	if not zettels:
		print('no links provided for writing'); return
	for zettel in zettels: #swaps tag ID with z_id
		entry_list.append((z_id, zettel[0]))
	incr_add_to_db(entry_list, insert_links, current_db_path)
	
#▒▒▒▒▒▒▒▒▒▒▒▒ READING DB OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def read_whole_zettel(z_id):
	zettel = read_main_id(z_id)
	try: title = zettel[0][1]; body = zettel[0][3]
	except IndexError: 
		title ='<no title / corrupted title>';
		body ='<no text body / corrupted text body>'
	tags = str(read_tags_z_id(z_id)) 
	links_from = str(read_links_z_id_from(z_id))
	return marker_title + '\n' + title + '\n\n' \
	+ marker_body+ '\n' + body + '\n\n' \
	+ marker_tags+ '\n' + tags + '\n\n' \
	+ marker_links+ '\n' + links_from

def read_links_z_id_from(z_id): return query_db(z_id, select_links_z_id_from, current_db_path)
def read_links_z_id_to(z_id): return query_db(z_id, select_links_z_id_to, current_db_path)

def read_invalid_links_all(): return query_db(None, select_invalid_links_all, current_db_path)

def read_taglist_id(id): return query_db(id, select_taglist_id, current_db_path)
def read_taglist_all(): return query_db(None, select_taglist_all, current_db_path)
def read_taglist_tags_like(name): return query_db('%'+name+'%', select_taglist_tag_like, current_db_path)

def read_tags_all_dist(): return query_db(None, select_tags_all_dist, current_db_path)
def read_tags_z_id(z_id): return query_db(z_id, select_tags_z_id, current_db_path)
def read_tags_tag_like(name): return query_db('%'+name+'%', select_tags_tag_like, current_db_path)

def read_main_id(id): return query_db(id, select_main_id, current_db_path)
def read_main_z_path(name): return query_db(name, select_main_z_path, current_db_path)
def read_main_all(): return query_db(None, select_main_all, current_db_path)
def read_main_z_title_like(name): return query_db('%'+name+'%', select_main_z_title_like, current_db_path)
def read_main_z_path_like(name): return query_db('%'+name+'%', select_main_z_path_like, current_db_path)
def read_main_z_body_like(name): return query_db('%'+name+'%', select_main_z_body_like, current_db_path)

#▒▒▒▒▒▒▒▒▒▒▒▒ REWRITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
#called by 'edit' functions
def rewrite_main_z_body(id, text):
	add_to_db([text, id], update_main_z_body, current_db_path)
	
def rewrite_main_z_title(id, title):
	add_to_db([title, id], update_main_z_title, current_db_path)

def rewrite_links_from(z_id, zettels): 
	remove_links_from(z_id)
	write_links_from(z_id, zettels)
	
def rewrite_tags(z_id, tags): 
	remove_tags_z_id(z_id)
	write_tags(z_id, tags)
	rescan_taglist() #might contain new tags or remove old
	
def rename_tag(tag, name): 
	add_to_db([name, tag], update_tags_tag, current_db_path)
	rescan_taglist() #reflect changes
	
#▒▒▒▒▒▒▒▒▒▒▒▒ REMOVE / REBUILD OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def rescan_taglist(): #after tag edit
	tags = []
	delete_from_db(None, delete_taglist_all, current_db_path)
	for entry in read_tags_all_dist():
		tags.append((entry[2],)) #need only names
	incr_add_to_db(tags, insert_taglist, current_db_path)
	
def rescan_meta(): #after any edit
	print()

def remove_invalid_links_all(): #after zettel removal, or optional
	delete_from_db(None, delete_invalid_links_all, current_db_path)

def remove_links_from(z_id): #after zettel removal, or optional
	delete_from_db(z_id, delete_links_z_id_from, current_db_path)
	
def remove_links_to(z_id): #after zettel removal, or optional
	delete_from_db(z_id, delete_links_z_id_to, current_db_path)
	
def remove_tags_z_id(z_id): #after zettel removal, or optional
	delete_from_db(z_id, delete_tags_z_id, current_db_path)
	rescan_taglist() #might remove all tag instances
	
def remove_tags_tag(name): #after zettel removal, or optional
	delete_from_db(name, delete_tags_tag, current_db_path)
	rescan_taglist() #removes all instances

#▒▒▒▒▒▒▒▒▒▒▒▒ ZETTEL / TAG WRITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def write_ext(option, inject_text):
	written = ''
	with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
		if inject_text: 
			try: tf.write(inject_text)
			except TypeError: tf.write(inject_text.encode("utf-8"))
			finally: tf.flush()
		try: subprocess.call([option, tf.name])
		except: print('no command found:', option); return written #failed
		finally:
			tf.seek(0); written = tf.read().decode("utf-8")
	return written.strip() #succeeded
	
def write_with_editor(inject_text):
	if default_editor == 'python': return s_prompt('enter text')
	while True:
		print_writer_options()
		inp = c_prompt('select editor')
		if inp == '': return write_ext(default_editor, inject_text)
		elif inp == 'v': return write_ext('vim', inject_text)
		elif inp == 'n': return write_ext('nano', inject_text)
		elif inp == 'e': return write_ext('emacs', inject_text)
		elif inp == 'i': return s_prompt('enter text')
		elif inp == "q": return None
	
def make_new_zettel():
	global sub_menu_depth; sub_menu_depth += 1
	z_title = ''
	z_body = ''
	while not z_title: z_title = write_with_editor(None)
	while not z_body: z_body = write_with_editor(None)
	
	print_zettels_select(); p()
	zettels_linked = zettel_picker()
	print_tags_select(); p()
	tags = tag_picker()
	
	#generate filename for export feature
	path_length = 30
	z_path = z_title
	if len(z_path) > path_length: z_path = z_path[0:path_length]
	z_path = z_path.strip().replace(' ', '_')
	z_path = re.sub(r'(?u)[^-\w.]', '_', z_path) 
	z_path += '.md'
	z_id = write_zettel(z_title, z_path, z_body)
	write_tags(z_id, tags)
	write_links_from(z_id, zettels_linked)
	#update meta
	#find it and enter ops sub menu
	new_zettel = read_main_id(z_id)[0]
	zettel_ops(new_zettel, False)

def make_new_tag():
	tag = ''; conf = ''
	while not tag: tag = write_with_editor(None)
	while conf =='':
		print('New tag:', tag)
		conf = c_prompt('is this correct?')
	t_id = write_taglist_tag([(tag,)])
	return (t_id, tag)

#▒▒▒▒▒▒▒▒▒▒▒▒ EDITING OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def zettel_picker(): #add ops to edit the list properly
	zettels = [] 
	try: zettels += search_zettels()
	except NameError: pass
	return zettels
	
def tag_picker(): #add ops to edit the list properly
	tags = [] 
	try: tags += search_tags()
	except NameError: pass
	return tags
	
def edit_main_z_title(z_id, z_title):
	print('write new title')
	new_title = ''
	while not new_title: new_title = write_with_editor(z_title)
	rewrite_main_z_title(z_id, new_title)
	
def edit_main_z_body(z_id, z_body):
	print('write new body')
	new_body = ''
	while not new_body: new_body = write_with_editor(new_body)
	rewrite_main_z_body(z_id, new_body)
	
def edit_links_z_id_from(z_id):
	print('editing links')
	zettels = zettel_picker()
	rewrite_links_from(z_id, zettels)
	
def edit_tags_z_id(z_id): #zettel ops only
	print('editing tags')
	tags = tag_picker()
	rewrite_tags(z_id, tags)
	
#▒▒▒▒▒▒▒▒▒▒▒▒ ANALYZE OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def tree():
	#str
	os.system('tree'+' '+path)
	
def review():
	print_start_check(); errors = False
	if not os.path.isfile(current_db_path): print_no_db_warn(); return
	if print_zettels_warnings(None, select_no_titles_all): print_no_titles_warn(); errors = True
	if print_zettels_warnings(None, select_no_bodies_all): print_no_bodies_warn(); errors = True
	if print_zettels_warnings(None, select_no_links_all): print_no_links_warn(); errors = True
	if print_zettels_warnings(None, select_self_links_all): print_self_links_warn(); errors = True
	if read_invalid_links_all():
		print_invalid_links();
		inp = c_prompt("discard invalid links? ('yes' to proceed)")
		if inp == 'yes': remove_invalid_links_all(); print_invalid_links_removed()
		else: print_invalid_links_not_removed(); errors = True
	if not errors: print_check_passed()

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
		
def zettel_ops(zettel, allow_submenu):
	global sub_menu_depth; 
	if not allow_submenu: sub_menu_depth += 1
	else: pass
	z_id = zettel[0]; z_title = zettel[1]; z_body = zettel[3]
	if sub_menu_depth < 2: print_whole_zettel(z_id); print_zettel_ops() #init
	else: print_whole_zettel(z_id); print_zettel_ops_lim() #init
	while True:
		inp = c_prompt('')
		if sub_menu_depth < 2:
			if inp == 'q': sub_menu_depth -= 1; return
			elif inp == 'n': edit_main_z_title(z_id, z_title)
			elif inp == 'b': edit_main_z_body(z_id, z_body)
			elif inp == 'l': edit_links_z_id_from(z_id)
			elif inp == 't': edit_tags_z_id(z_id)
		else:
			if inp == 'q': sub_menu_depth -= 1; return
		print_whole_zettel(z_id); 
		if sub_menu_depth < 2: print_zettel_ops()
		else: print_zettel_ops_lim()
		
def tag_ops(tag):
	global sub_menu_depth; sub_menu_depth = 0
	tag_id = tag[0];
	result = list_by_tag(tag_id) #if it returns - tag is good
	zettels = result[0]; titles = result[1]; listed_tag = result[2]
	while True:
		print_zettels_under_tag(titles, listed_tag)
		if zettel_select_sub_menu(zettels): return
		
			
def main_menu():
	global sub_menu_depth
	print_main_ops()
	while True:
		sub_menu_depth = 0
		inp = c_prompt('MENU')
		if inp == "i": print_db_meta(); p()
		elif inp == "n": make_new_zettel(); p()
		elif inp == "z": search_zettels(); 
		elif inp == "t": search_tags(); 
		elif inp == "r": review(); p()
		elif inp == "tree": tree(); p()
		elif inp == "init": init_new_db(); p()
		elif inp == "temp": make_template(); p()
		elif inp == "test": make_test_zettels(); p()
		elif inp == "import": import_zettels(); p()
		elif inp == "compile": compile_myself(); p()
		elif inp == "git": git_menu(); 
		elif inp == "q": quit()
		print_main_ops()

#▒▒▒▒▒▒▒▒▒▒▒▒ SEARCH OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def search_zettels():
	flag = ''
	while True:
		print_how_to_search_zettel()
		inp = c_prompt('')
		if inp == 'n': flag = 'name'; break
		if inp == 't': flag = 'tag'; break
		if inp == 'b': flag = 'body'; break
		if inp == 'q': return
	entries = []
	while True:
		s = find_zettel(flag)
		if s['found'] or s['stop']: 
			if s['found']: entries.append(s['found'])
			if s['stop']: break
			zettel_ops(s['found'], False)
			print_zettel_search_confirmation(entries)
			inp = c_prompt('search for more?')
			if inp == 'q': break
			if inp == 'n': flag = 'name'
			if inp == 't': flag = 'tag'
			if inp == 'b': flag = 'body'
			if inp == 'c': entries = []
	entries = list(dict.fromkeys(entries)) #dedup
	return entries
	
def search_tags():
	entries = []
	while True:
		s = find_tags()
		if s['found'] or s['stop']: 
			if s['found']: entries.append(s['found'])
			if s['stop']: break
			tag_ops(s['found'])
			print_tag_search_confirmation(entries)
			inp = c_prompt('search for more?')
			if inp == 'q': break
			if inp == 'c': entries = []
	entries = list(dict.fromkeys(entries)) #dedup
	return entries

def zettel_select_sub_menu(zettels): #when zettel list provided
	print_select_zettel_commands()
	zettel = None
	inp = c_prompt('')
	try: 
		zettel = zettels[int(inp)-1]
		print_found_zettels(zettel, int(inp))
		zettel_ops(zettel, True)
	except (ValueError, IndexError): pass
	if inp == "q": return True

def zettel_search_sub_menu(s):
	print_search_zettel_commands()
	inp = c_prompt('')
	try: 
		print_found_zettels(s['entries'][int(inp)-1], int(inp))
		s['found'] = s['entries'][int(inp)-1]
	except (ValueError, IndexError): pass
	finally:
		if inp == "c": s['name'] = ''; s['inp'] = ''; s['entries'] = read_main_all() #reset
		if inp == "q": s['stop'] = True
	return s
	
def tag_search_sub_menu(s):
	print_search_tag_commands()
	inp = c_prompt('')
	try: 
		print_found_tags(s['entries'][int(inp)-1], int(inp))
		s['found'] = s['entries'][int(inp)-1]
	except (ValueError, IndexError): pass
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
		if flag == 'name': s['entries'] = read_main_z_title_like(s['name'])
		elif flag == 'body': s['entries'] = read_main_z_body_like(s['name'])
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
			s = zettel_search_sub_menu(s); 
			if not s['stop']:
				print_many_zettels_or_return(s['entries']); 
		if s['found'] or s['stop']: return s
		if flag == 'tag': print_all_tags()
		s['inp'] = s_prompt('searching zettel by ' + flag +': '+ s['name'])
		
def find_tags():
	s = {'found': None, 'name': '', 'inp': '', 'entries': [], 'stop': False}
	s['entries'] = read_taglist_all()
	while True:
		if s['inp'] != ':': s['name'] += s['inp']
		s['entries'] = read_taglist_tags_like(s['name'])
		s['found'] = print_many_tags_or_return(s['entries'])
		if s['inp'] == ':': 
			s = tag_search_sub_menu(s); 
			if not s['stop']:
				print_many_tags_or_return(s['entries']); 
		if s['found'] or s['stop']: return s
		s['inp'] = s_prompt('searching existing tag: '+ s['name'])

#▒▒▒▒▒▒▒▒▒▒▒▒ LIST OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def list_by_tag(tag_id):
	titles = []; tagged_zettels = []
	listed_tag = read_taglist_id(tag_id)[0][1]
	tags = read_tags_tag_like(listed_tag)
	for tag in tags:
		z_id = tag[1]
		zettels = read_main_id(z_id)
		z_title = zettels[0][1]
		tagged_zettels.append(zettels[0])
		titles.append(z_title)
	return (tagged_zettels, titles, listed_tag,)
	
def str_from_list(sort_flag, draw_flag, enumerate, init, i):
	strn = ''; fin = []; num = 1; dot = '. ';
	for entry in init: fin.append(entry[i])
	if sort_flag: fin.sort()
	if draw_flag:
		le = ', '
		if enumerate:
			for entry in fin: strn += str(num)+dot+str(entry)+le; num += 1
		else:
			for entry in fin: strn += str(entry) + le
	else:
		le = '\n'
		if enumerate:
			for entry in fin: strn += str(num)+dot+str(entry)+le; num += 1
		else:
			for entry in fin: strn += str(entry) + le
	return strn

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
	print_importing_warn()
	inp = s_prompt('local folder name')
	if not os.path.isdir(inp):
		print_importing_failed(); return #failed
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
						c.execute(select_main_z_path, (z_path,))
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
						c.execute(select_main_z_path, (z_path,))
						current_zettel_id = c.fetchall()[0][0]
						#see if links point out to existing nodes
						for link_path in links:
							#destination zettel
							c.execute(select_main_z_path, (link_path,))
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
				t = time_end - time_start
				print_db_meta(db_name_imported)
				print_importing_succeeded(database_name, t)
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

#▒▒▒▒▒▒▒▒▒▒▒▒ FILE & TEST OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def compile_myself():
	py_compile.compile(
		file='zettel-pycli.py', 
		cfile='zettel-pycli.pyc',
		optimize=2,)
	
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

#▒▒▒▒▒▒▒▒▒▒▒▒ PRINT OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
#DB ERROR CHECK
def print_start_check():
	cl_divider()
	print('starting to check the database')
	
def print_no_db_warn():
	cl_divider()
	print('no database matching the name provided in this script')
	print('check the name in the script header, or import or')
	print('initiate the database via respective commands')
	
def print_no_titles_warn(): print('\nthere are zettels without titles listed above, inspect')
def print_no_bodies_warn(): print('\nthere are zettels without text listed above, fill them')
def print_no_links_warn(): print('\nthere are unlinked zettels listed above, link them')
def print_self_links_warn(): print('\nthere are zettels linking to themselves listed above')
	
def print_invalid_links_warn():
	print('\nthere are corrupt links in your zettels')
	print('this error should occur after importing .md zettels')
	print('which is why you shall fix the links in your .md files')
	print('and then re-import them to database again')
	print('optionally, you may discard those links')

def print_invalid_links_not_removed(): divider(); print('invalid links warnings are kept')
def print_invalid_links_removed(): divider(); print('invalid links warnings are removed')

def print_check_passed(): divider(); print('all good, no corrupt links or unlinked zettels')
def print_db_exists(): cl_divider(); print('a database like this already exists, aborting')
def print_importing_warn():
	cl_divider()
	print('you are about to import your .md zettels to database')
	print('make sure the folder with zettels is in the same')
	print('directory as this application')
	print('folders with nested sub-folders are not supported')
	print('that will lead to corrupted links')

def print_importing_succeeded(database_name, t):
	divider()
	print('success, database built in:', t, 's')
	print('to use the database rename file to match:', database_name+'.db')
	print('this is the name given in the application options')
	print('do not forget to review the database for errors')

def print_importing_failed():
	divider()
	print('wrong folder name, aborting...')
	
#TEST
def print_test_warn():
	cl_divider()
	print('make sure you have backed up your journal folder')
	print('this will generate a batch of zettel .md cards in it')
	print('you will have to import them back into a database')
	
def print_test_wrong_input(): cl_divider(); print('make sure you enter numbers')
def print_made_tests():
	cl_divider()
	print('generated a number of test zettels')
	print("don't forget to import them into the database")

#WRITING ZETTEL
def print_zettels_select(): cl_divider(); print('select zettels that you want to LINK to')
def print_tags_select():
	cl_divider()
	print('select a suitable TAG for your zettel')
	print('you can either search for existing tag')
	print('or write a new one if no suitable found')

#MAIN MENU
def print_main_ops():
	cl_divider()
	print('(i) - show statistics')
	print('(z) - find zettel to enter the database')
	print('(t) - browse tags in the database')
	print('(r) - review zettels for errors in links and content')
	print('(n) - start writing a new zettel')
	print('(tree) - use "tree" command to show files')
	print('(init) - make a new database (name in script header)')
	print('(temp) - generate a template zettel')
	print('(test) - generate a batch of test zettels')
	print('(import) - import .md zettels to the database')
	print('(compile) - compile this .py into .pyc for safety')
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
	print_q()

#SELECTING WRITER
def print_writer_options():
	cl_divider()
	print('to use any of provided external editors,')
	print('make sure they are installed\n')
	print('() - write with user-defined editor (see script header)')
	print('(v) - write using vim')
	print('(e) - write using emacs')
	print('(n) - write using nano')
	print('(i) - fallback write with python input')
	
#SEARCHING
def print_searching():
	divider()
	print('keep narrowing your search by entering more characters')
	print("or enter ':' for search tools or to return")
	
#SEARCHING ZETTEL
def print_how_to_search_zettel():
	cl_divider()
	print('how do you want to find a zettel?')
	divider()
	print('(n) - by zettel name (title)')
	print('(t) - by tag')
	print('(b) - by text body')
	print_q()

def print_search_zettel_commands():
	divider()
	print("'number' - select entry")
	print("(c) - clear search query and start again")
	print_qc()
	
def print_select_zettel_commands():
	divider()
	print("'number' - inspect entry")
	print_qc()

def print_zettel_ops():
	divider()
	print('(n) - edit title (name)')
	print('(b) - edit text body')
	print('(l) - edit links')
	print('(t) - edit tags')
	print_qc()
	
def print_zettel_ops_lim():
	divider()
	print_qc()
	
#SEARCHING TAGS
def print_search_tag_commands():
	divider()
	print("'number' - select entry")
	print('(n) - add a new tag not from list')
	print("(c) - clear search query and start again")
	print_qc()
	
def print_tag_ops():
	divider()
	print_qc()
	
def print_tag_ops_lim():
	divider()
	print_qc()

#▒▒▒▒▒▒▒▒▒▒▒▒ OTHER PRINTING ▒▒▒▒▒▒▒▒▒▒▒▒▒
def print_db_meta(db_path=current_db_path):
	if os.path.isfile(db_path):
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
	else: print_no_db_warn()
	
def print_whole_zettel(z_id):
	cl_divider()
	print(read_whole_zettel(z_id))
	
def print_all_tags():
	enumerate = False
	strn = str_from_list(sort_tags, draw_tags_in_line, enumerate, read_taglist_all(), 1)
	divider()
	print('available tags:'); print(strn);

def print_selected_zettels(entries):
	enumerate = True
	strn = str_from_list(sort_titles, draw_titles_in_line, enumerate, entries, 1)
	cl_divider()
	print('viewed | selected zettels:'); print(strn)
	
def print_selected_tags(entries):
	enumerate = True
	strn = str_from_list(sort_tags, draw_tags_in_line, enumerate, entries, 1)
	cl_divider()
	print('viewed | selected tags:'); print(strn);

def print_zettel_search_confirmation(entries):
	print_selected_zettels(entries)
	divider()
	print('() - resume search')
	print('(n) - switch to search by title (name)')
	print('(t) - switch to search by tag')
	print('(b) - switch to search by text body')
	print('(c) - clear search queue and restart search')
	print_qc()
	
def print_tag_search_confirmation(entries):
	print_selected_tags(entries)
	divider()
	print('() - resume search')
	print('(c) - clear search queue and restart search')
	print_qc()
	
def print_found_zettels(zettel, val): print('selected:', str(val)+'.', zettel[1])
def print_found_tags(tag, val): print('selected:', str(val)+'.', tag[1])

def print_many_zettels_or_return(zettels):
	num = 1
	if len(zettels) > 1:
		cl_divider()
		for zettel in zettels:
			print(str(num)+'.', zettel[1])
			num += 1
		print('\ntotal search hits:', len(zettels)); print_searching()
	elif len(zettels) == 0: 
		cl_divider()
		print("no zettel found, ':' for options");
	elif len(zettels) == 1: 
		print_found_zettels(zettels[0], '')
		return zettels[0] #return what was found by narrowing down
		
def print_many_tags_or_return(tags):
	num = 1
	if len(tags) > 1:
		cl_divider()
		for tag in tags:
			print(str(num)+'.', tag[1])
			num += 1
		print('\ntotal search hits:', len(tags)); print_searching()
	elif len(tags) == 0: 
		cl_divider()
		print("no tags found, ':' for options");
	elif len(tags) == 1: 
		print_found_tags(tags[0], '')
		return tags[0] #return what was found by narrowing down

def print_zettels_under_tag(titles, tag):
	num = 1
	cl_divider()
	for title in titles:
		print(str(num)+'.', title)
		num += 1
	print('\nzettels under tag:', tag, '-', len(titles))
	
def print_invalid_links():
	entries = read_invalid_links_all()
	if entries == []: return False
	same_zettel = False; id_prev = None; num = 1
	divider()
	for entry in entries:
		zettel = read_main_id(entry[1])
		z_id = zettel[0][0]; z_title = zettel[0][1]; z_path = zettel[0][2]; 
		invalid_link_name = entry[2]
		if z_id == id_prev: same_zettel = True
		if same_zettel:
			print('   └─', invalid_link_name)
			same_zettel = False
		else:
			print()
			print(str(num)+'.', 'id:', str(z_id) + ',', z_title)
			print('   file:', z_path)
			print('   corrupt links:')
			print('   └─', invalid_link_name)
			num += 1
		id_prev = z_id
	print_invalid_links_warn()
	return True
		
def print_zettels_warnings(query, exec_str): #for other kinds of errors
	entries = query_db(query, exec_str, current_db_path); num = 1
	if entries == []: return False;
	divider()
	for entry in entries:
		z_id = entry[1]; z_title = read_main_id(z_id)[0][1]
		print(str(num)+'.', 'id:', str(z_id) + ',', z_title)
		num += 1
	return True

#▒▒▒▒▒▒▒▒▒▒▒▒ STANDARD PROMPTS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def c_prompt(prompt): divider(); return input(prompt+" : ").strip()
def s_prompt(prompt): divider(); return input(prompt+" > ").strip()
def p(): divider(); input("enter to continue...").strip()
def print_qc(): print('(q) - return | confirms selection')
def print_q(): print('(q) - return')

#▒▒▒▒▒▒▒▒▒▒▒▒ CLEAR SCREEN AND DIVIDER ▒▒▒▒▒▒▒▒▒▒▒▒▒
def divider(): 
	d_line = '-------------------------------------------------------'
	print(d_line)
def cl(): os.system('cls' if os.name == 'nt' else 'clear')
def cl_divider(): cl(); divider()


#▒▒▒▒▒▒▒▒▒▒▒▒ START ▒▒▒▒▒▒▒▒▒▒▒▒▒
main_menu()