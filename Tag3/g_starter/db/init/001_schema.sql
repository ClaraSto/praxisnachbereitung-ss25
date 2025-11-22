create table if not exists Device_Type (
    type_id integer primary key,
    device_name varchar(32)
);

create table if not exists Location (
    location_id integer primary key,
    location_name varchar(32) not null
);

create table if not exists Person (
    personal_nr integer primary key,
    person_name varchar(100) not null
);

create table if not exists Device (
    serial_number integer primary key,
    device_type_id integer not null references Device_Type (type_id),
    location_id integer not null references Location (location_id),
    note text
);

create table if not exists Assignment (
    device_id integer not null references Device (serial_number),
    person_id integer not null references Person (personal_nr),
    issued_at date not null,
    returned_at date check (returned_at >= issued_at or returned_at is null)
);

insert into Device_Type values
(2001,'Geiger_Counter'),
(2002,'Big_Spoon'),
(2003,'GabeCube');

insert into Location values
(3001,'IT'),
(3002,'Produktion'),
(3003,'Research');

insert into Person values
(1001,'Angus Young'),
(1002,'Sherlock Holmes'),
(1003,'Walter White');

insert into Device values
(4001,2002,3003,'Do not break again.'),
(4002,2001,3002,'For the Big Cereal'),
(4003,2003,3001,'Walter, stop gaming Walter.');

insert into Assignment values
(4002,1002,now()::date, null),
(4001,1003,'2023-10-11','2023-10-15');