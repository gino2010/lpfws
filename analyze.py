#!/usr/bin/env python
# -*- coding:utf-8 -*-
#version 1.1
import glob
import sqlite3
import re
import sys

__author__ = 'gino'
LOG_FILE = ""
DB_FILE = ""


def main():
    files = glob.glob('run.log.????-??-??')
    for idx, val in enumerate(files):
        print("{}:{}".format(idx, val))
    print("exit: abort operation")
    fi = ""
    while True:
        fi = raw_input("please select file by index[exit]: ") or "exit"
        if fi == "exit":
            sys.exit()
        if fi.isdigit() and int(fi) < len(files):
            break
    log_file = files[int(fi)]
    return log_file


def data_into_base(log_file):
    tflag = True
    db_file = '%s.db' % log_file
    conn = sqlite3.connect(db_file)
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE logdata (ip TEXT NOT NULL, dt TEXT NOT NULL)''')
    except sqlite3.OperationalError as e:
        print(e.message)
        tflag = False
    finally:
        conn.commit()
        conn.close()
    if tflag:
        conn = sqlite3.connect(db_file)
        regex = re.compile("(.*)from ip(.*)")
        print("start to insert into database")
        linecount = 0
        with open(log_file, "r") as fo:
            for line in fo:
                result = regex.search(line)
                if result is not None:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO logdata (ip, dt) VALUES (?, ?)", (
                                  re.findall(r'[0-9]+(?:\.[0-9]+){3}', line)[0], line[0:19]))
                        linecount += 1
                    except sqlite3.OperationalError as e:
                        print(e.message)
                    finally:
                        pass
            conn.commit()
            conn.close()
        print("finished, %s lines inserted." % linecount)
    return db_file


def report(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT dt, count(*) AS num FROM logdata GROUP BY dt ORDER BY num DESC LIMIT 5")
    print("----Report----")
    print("Concurrent Requests Top 5 by Second:")
    id = 0
    dt_list = []
    for row in c:
        print("{}.Datetime:{} Count:{}".format(id, row[0], row[1]))
        id += 1
        dt_list.append(row[0])

    c.execute("SELECT ip, count(*) AS num FROM logdata GROUP BY ip ORDER BY num DESC")
    print("\nList IP of Request and Request Count:")
    for row in c:
        print("IP:{} Count:{}".format(row[0], row[1]))

    return dt_list


def detail(db_file, dt_list):
    while True:
        dt = raw_input("\nWant to expand one concurrent collection?[N]: ") or "N"
        if dt in ['N', 'n']:
            sys.exit()
        if dt.isdigit() and int(dt) < len(dt_list):
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            c.execute("SELECT * FROM logdata WHERE dt = ?", (dt_list[int(dt)],))
            print("\nDetail for one concurrent")
            for row in c:
                print("Datetime:{} IP:{}".format(row[1], row[0]))

if __name__ == '__main__':
    LOG_FILE = main()
    DB_FILE = data_into_base(LOG_FILE)
    dt_list = report(DB_FILE)
    detail(DB_FILE, dt_list)