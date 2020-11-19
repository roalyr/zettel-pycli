#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
kasten_name = "my_vault"


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
import os, fnmatch, shutil, pathlib, sqlite3, time, re
from sqlite3 import Error

path = os.path.join(os.getcwd(), kasten_name)
db_path = os.path.join(os.getcwd(), kasten_name + '_index.db')
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
create_main_table = '''
	CREATE TABLE IF NOT EXISTS main (
		id integer PRIMARY KEY,
		z_title text NOT NULL,
		z_path text NOT NULL
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

create_tags_table = '''
	CREATE TABLE IF NOT EXISTS tags (
		id integer PRIMARY KEY,
		z_id integer NOT NULL,
		tag text NOT NULL
	); '''

insert_main = '''
	INSERT INTO main (
		z_title,
		z_path
	)
	VALUES(
		?, ?
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
	
def make_new():
	inp = input("enter zettel name » ").strip()
	f = open(path + "/" + inp + '.md', "w")
	f.write(zettel_template)
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
		'tags' : [],
		'links' : [],
	}
	
	# open the file and read through it line by line
	f = open(z_path, 'r')
	
	#a switch flag to read links in tge end of the file
	reading_title = False
	reading_links = False
	reading_tags = False
	
	#parse keywords
	for line in f:
		
		if marker_body in line:
			reading_title = False
			reading_tags = False
			reading_links = False
			continue
	
		if marker_title in line:
			reading_title = True
			reading_tags = False
			reading_links = False
			continue
		
		if marker_tags in line:
			reading_title = False
			reading_tags = True
			reading_links = False
			continue
	
		if marker_links in line:
			reading_title = False
			reading_tags = False
			reading_links = True
			continue
		
		if reading_title:
			data['title'] += line.strip()
			
		if reading_tags:
			data['tags'] += find_comma_separated(line)
			
		if reading_links:
			data['links'] += find_md_links(line)
	
	return data
	
def parse_zettel_body(z_path):
	# open the file and read through it line by line
	f = open(z_path, 'r')
	
	zettel_body = ''
	reading = False
	
	#parse keywords
	for line in f:
		
		if marker_body in line:
			reading = True
			continue
	
		if (marker_title in line) or (marker_tags in line) or (marker_links in line):
			reading = False
			continue
		
		if reading:
			zettel_body += line
	
	return zettel_body
	
	
	
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
				c.execute(create_main_table)
				c.execute(create_links_table)
				c.execute(create_invalid_links_table)
				c.execute(create_tags_table)
				
				#populate tables
				time_start = time.time()
				links = []
				
				#main table
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name:
							continue
							
						full_path = os.path.join(root, name)
						z_path = name
						z_title = parse_zettel_metadata(full_path)['title']
						c.execute(insert_main, (z_title, z_path,))
						
				conn.commit()
				
				#links table, with check
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name:
							continue
						
						#get the links to which zettel refers to
						full_path = os.path.join(root, name)
						links = parse_zettel_metadata(full_path)['links']
						
						#get the current zettel id
						c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (name,))
						current_zettel_id = c.fetchall()[0][0]
						
						#see if links point out to existing nodes
						for z_path_to in links:
							c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (z_path_to,))
							found_zettel = c.fetchall()
							
							if found_zettel:
								valid_zettel_id = found_zettel[0][0]
								c.execute(insert_links, (current_zettel_id, valid_zettel_id,))
							
							else:
								c.execute(insert_invalid_links, (current_zettel_id, z_path_to,))
				
				conn.commit()
				
				#tags table
				for root, dirs, files in os.walk(path):
					for name in files:
						if name == zettel_template_name:
							continue
						
						#get the links to which zettel refers to
						full_path = os.path.join(root, name)
						tags = parse_zettel_metadata(full_path)['tags']
						
						#get the current zettel id
						c.execute("SELECT DISTINCT * FROM main WHERE z_path=?", (name,))
						current_zettel_id = c.fetchall()[0][0]
						
						#write the tags to table
						for tag in tags:
							c.execute(insert_tags, (current_zettel_id, tag,))
						
				conn.commit()
				
				time_end = time.time()
				print('database rebuilt in: ', time_end - time_start)
			
			except Error as e:
				print(e)
			conn.close()



#▒▒▒▒▒▒▒▒▒▒▒▒ ANALYSIS OPS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def increm_input_title_name():
	name = ''
	
	while True:
		inp = input(name + " < ")
		os.system('clear')
		#pick up by number in list
		try:
			if inp[0] == ":": 
				val = int(inp[1:])
				if entry[1] != '':
					title = entry[1]
					print()
					print('selected:', str(val)+'.', entry[2])
					print(' ╰ ' + title)
				else:
					print()
					print('selected:', str(val)+'.', entry[2])
				print('what shall we do next?')
				get_exact = "SELECT * FROM main WHERE id = " + str(entries[val][0])
				row = query_db(get_exact)
				file_path = os.path.join(path, row[0][2])
				stop = False
				print_zettel_ops()
				while not stop:
					stop = zettel_ops(inp, file_path)
				else:
					return
		except:
			pass
		
		name += inp
		num = 0
		
		#or keep iterating tye query
		#show all if no input
		if name == '':
			get_all = "SELECT * FROM main"
			entries = query_db(get_all)
		#or find by name or title
		else:
			get_by_name = "SELECT * FROM main WHERE z_path LIKE '%"+name+"%' OR z_title LIKE '%"+name+"%'"
			entries = query_db(get_by_name)
		
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
			print('or enter :number to pick an entity from the query list')
			print(divider)
			
		elif len(entries) == 1: 
			entry = entries[0]
			print()
			if entry[1] != '':
				title = entry[1]
				print()
				print('found:', entry[2])
				print(' ╰ ' + title)
			else:
				print()
				print('found:', entry[2])
			print('what shall we do next?')
			get_exact = "SELECT * FROM main WHERE id = " + str(entries[0][0])
			row = query_db(get_exact)
			file_path = os.path.join(path, row[0][2])
			stop = False
			print_zettel_ops()
			while not stop:
				stop = zettel_ops(inp, file_path)
			else:
				return
		
		#break if neither name matches
		elif len(entries) == 0: 
			print('no zettel found')
			return
		


def get_entry_num(pattern):
	num = 0
	for root, dirs, files in os.walk(path):
		for name in files:
			if name == zettel_template_name:
				continue
			if fnmatch.fnmatch(name, pattern):
				num += 1
	return num
	
def get_warn_num():
	num = 0
	return num
	
def print_zettel_ops():
	print('')
	print(banner_zettel_ops)
	print('() - read current zettel')
	print(banner_zettel_ops)
	print('')
	print('(q) - quit')
	
def zettel_ops(inp, file_path):
	inp = input("ZETTEL OPS ('?' for commands) » ").strip()
	
	if inp == "":
		os.system('clear')
		print(divider)
		print(parse_zettel_body(file_path))
		print(divider)
	elif inp == "?":
		print_zettel_ops()
	elif inp == 'q':
		return True
		


			
#▒▒▒▒▒▒▒▒▒▒▒▒ FUNCTION WRAPPERS ▒▒▒▒▒▒▒▒▒▒▒▒▒
def sync():
	print(divider)
	update_db()
	entries_num = get_entry_num('*.md')
	warnings_num = get_warn_num()
	print('current number of your precious zettels is:', entries_num)
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
	
def make_new_zettel():
	zettel_name = make_new()
	print(divider)
	print('generated a new empty zettel from template:', zettel_name)
	print(divider)
	
def print_main_ops():
	print('')
	print(banner_main)
	print('(u) - update the index and show brief statistics')
	print('(n) - make new empty zettel')
	print('(f) - incrementally find zettel')
	print('(tree) - use "tree" command to show files')
	print('(temp) - generate a template zettel')
	print(banner_main)
	print('')
	print('(t) - git menu')
	print('(q) - quit')
		
#▒▒▒▒▒▒▒▒▒▒▒▒ MAIN MENU ▒▒▒▒▒▒▒▒▒▒▒▒▒
def main_menu():
	print_main_ops()
	
	while True:
		print('')
		inp = input("MAIN MENU ('?' for commands) » ").strip()
		print('')
				
		if inp == "u":
			os.system('clear')
			sync()
		if inp == "n":
			os.system('clear')
			make_new_zettel()
		if inp == "f":
			os.system('clear')
			find_zettel()
		if inp == "tree":
			os.system('clear')
			tree()
		if inp == "temp":
			os.system('clear')
			make_template()
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
