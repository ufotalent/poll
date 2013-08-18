drop table if exists users;
drop table if exists courses;
drop table if exists scores;
drop table if exists transactions;
create table users(
    uname text primary key,
    password char(33)
);

create table courses(
    cid integer primary key autoincrement,
    name text
);

create table scores(
    sid integer primary key autoincrement,
    uname text,
    cid integer,
    score integer,
    FOREIGN KEY(cid) REFERENCES courses(cid),
    FOREIGN KEY(uname) REFERENCES users(uname),
    CONSTRAINT c_ UNIQUE (cid, uname)
);

create table transactions(
    tid integer primary key autoincrement,
    mod_value integer,
    mod_time timestamp,
    mod_result integer,
    mod_reason text,
    sid integer,
    FOREIGN KEY(sid) REFERENCES scores(sid)
)

