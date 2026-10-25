CREATE TABLE event_details(
 installation TEXT NOT NULL,
 id TEXT NOT NULL,
 first_seen REAL NOT NULL,
 last_seen REAL NOT NULL,
 first_received REAL NOT NULL,
 received_at REAL NOT NULL,
 diagnostics TEXT NOT NULL DEFAULT '{}',
 PRIMARY KEY(installation,id),
 FOREIGN KEY(installation,id) REFERENCES events(installation,id) ON DELETE CASCADE
);
CREATE INDEX event_details_last ON event_details(last_seen);
