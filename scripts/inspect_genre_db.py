import sqlite3

db='C:/Users/Mert1/Desktop/GAME_HUB/GameHub/db.sqlite3'
con=sqlite3.connect(db)
cur=con.cursor()
try:
    cur.execute('SELECT rowid, genre FROM games_game')
    rows=cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('ERR', e)
finally:
    con.close()
