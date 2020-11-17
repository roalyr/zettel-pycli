import os, fnmatch, shutil, pathlib, sqlite3, time
from sqlite3 import Error

#▒▒▒▒▒▒▒▒▒▒▒▒ USER OPTIONS ▒▒▒▒▒▒▒▒▒▒▒▒▒
kasten_name = "my_vault"






#▒▒▒▒▒▒▒▒▒▒▒▒ SCRIPT BODY ▒▒▒▒▒▒▒▒▒▒▒▒▒
#Init
path = os.path.join(os.getcwd(), kasten_name)
pathlib.Path(path).mkdir(parents=True, exist_ok=True)

#Just fancy stuff
banner_git      = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒GIT MENU▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_log      = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒LOG▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_commit   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒COMMITTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_revert   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒REVERTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_hreset   = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒HARD RESETTING▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
banner_zettel     = '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ZETTEL MENU▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒'
divider = '-------------------------------------------------------'

#▒▒▒▒▒▒▒▒▒▒▒▒ GIT MENU ▒▒▒▒▒▒▒▒▒▒▒▒▒
def git_menu():

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
			
#▒▒▒▒▒▒▒▒▒▒▒▒ ZETTEL MENU ▒▒▒▒▒▒▒▒▒▒▒▒▒
def main_menu():
	
	def print_main_ops():
		print('')
		print(banner_zettel)
		print('() - update the index and show brief statistics')
		print('(tree) - use "tree" command to show files')
		print(banner_zettel)
		print('')
		print('(t) - git menu')
		print('(q) - quit')
	
	#Main sync function
	def flietype_sync(pattern, timestamp_file):
		
		#CREATE TABLE IF NOT EXISTS main (
		create_main_table = '''
			CREATE TABLE IF NOT EXISTS main (
				id integer PRIMARY KEY,
				zettel_title text NOT NULL,
				zettel_path text NOT NULL
		); '''
		
		create_link_table = '''
			CREATE TABLE IF NOT EXISTS links (
				id integer PRIMARY KEY,
				link_from integer NOT NULL,
				link_to integer NOT NULL
		); '''
		
		insert_main = '''
			INSERT INTO main (
				zettel_title,
				zettel_path
			)
			VALUES(
				?, ?
			) '''
			
		insert_links = '''
			INSERT INTO links (
				link_from,
				link_to
			)
			VALUES(
				?, ?
			) '''
			
		sql_u = '''
			UPDATE projects 
				SET
					name = ?
				WHERE
					id = ?
		'''
		
		#connect
		conn = None
		try:
			conn = sqlite3.connect(kasten_name+'.db')
			print(sqlite3.version)
		except Error as e:
			print(e)
		finally:
			if conn:
				try:
					c = conn.cursor()
					c.execute(create_main_table)
					c.execute(create_link_table)
					
					start = time.time()
					for i in range(0, 1000):
						zettel_title = 'zettel_' + str(i)
						zettel_path = path + zettel_title
						c.execute(insert_main, (zettel_title, zettel_path,))
					
					for i in range(0, 10000):
						link_from = i
						link_to = i+53
						c.execute(insert_links, (link_from, link_to,))
						
					end = time.time()
					print(end - start)
					#for i in range(0, 100000):
						#c.execute(sql_u, (str(i),i))
					
					conn.commit()
					
	
					#c.execute("SELECT * FROM main")
					c.execute("SELECT * FROM main WHERE zettel_title=?", ('zettel_1',))
					rows = c.fetchall()
					
					for row in rows:
						print(row)
						c.execute("SELECT * FROM links WHERE link_from=?", (row[0],))
						rows = c.fetchall()
						for row in rows:
							print(row)
							c.execute("SELECT * FROM main WHERE id=?", (row[2],))
							rows = c.fetchall()
							for row in rows:
								print(row)
					
				except Error as e:
					print(e)
				conn.close()
				os.system('rm *.db')
		
		
		
		queue_names = []
		timestamps_new = []
		timestamps_old = []
		
		#read existing timestamps
		try:
			timestamps_file = open(timestamp_file, 'r') 
			lines = timestamps_file.readlines() 
			for line in lines: 
				timestamps_old.append(line.strip())
		except:
			print(divider)
			print('no timestamp file: '+timestamp_file+' exist, it will be created')
			print(divider)
			
		#get the current timestamps & paths from source directory
		for root, dirs, files in os.walk(path):
			for name in files:
				if fnmatch.fnmatch(name, pattern):
					queue_names.append(name)
					file_path = os.path.join(root, name)
					timestamps_new.append(os.path.getmtime(file_path))
					
		#show added or modified files
		for entry in range(len(timestamps_new)):
			try:
				if float(timestamps_new[entry]) != float(timestamps_old[entry]):
					print('modified:', timestamps_new[entry], queue_names[entry])
			except:
				print('added:', timestamps_new[entry], queue_names[entry])
		
		#write (new) timestamps
		with open(timestamp_file, 'w') as f:
		    for item in timestamps_new:
		        f.write("%s\n" % item)
	
	def get_entry_num(pattern):
		num = 0
		for root, dirs, files in os.walk(path):
			for name in files:
				if fnmatch.fnmatch(name, pattern):
					num += 1
		return num
	
	#Functions-wrappers for commands
	#Higher-level functions
	def sync_files():
		flietype_sync('*.md', '.timestamp_md')
		
	
	def statistics():
		entries_num = get_entry_num('*.md')
		print(divider)
		print('current number of zettels is: ' + str(entries_num))
		print(divider)
		
	def tree():
		os.system('tree'+' '+path)
		print(divider)
		print('tree rendred')
		print(divider)
	
	#while True:
	print_main_ops()
	
	while True:
		print('')
		inp = input("MAIN MENU ('?' for commands) » ").strip()
		print('')
				
		if inp == "":
			os.system('clear')
			#update()
			sync_files()
			statistics()
		if inp == "tree":
			os.system('clear')
			tree()
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
