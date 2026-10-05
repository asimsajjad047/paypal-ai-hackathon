PRAGMA foreign_keys = ON;

-- Main table: details every part has
CREATE TABLE Part (
    PartID    INTEGER PRIMARY KEY,
    Name      TEXT NOT NULL,
    Brand     TEXT NOT NULL,
    Price     REAL CHECK (Price >= 0),
    Category  TEXT NOT NULL CHECK (Category IN
              ('CPU','Motherboard','RAM','GPU','PSU','Case','Cooler','Storage'))
);

-- Subtype tables: specs can be NULL (unknown) for imported parts
CREATE TABLE CPU (
    PartID                INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Socket                TEXT,
    TDP_W                 INTEGER,
    HasIntegratedGraphics INTEGER CHECK (HasIntegratedGraphics IN (0,1)),
    Cores                 INTEGER,
    BoostClock            REAL
);

CREATE TABLE Motherboard (
    PartID      INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Socket      TEXT,
    FormFactor  TEXT,
    RAMType     TEXT,
    RAMSlots    INTEGER,
    MaxRAM_GB   INTEGER,
    M2Slots     INTEGER
);

CREATE TABLE RAM (
    PartID            INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    RAMType           TEXT,
    Speed_MHz         INTEGER,
    ModuleCount       INTEGER,
    TotalCapacity_GB  INTEGER
);

CREATE TABLE GPU (
    PartID     INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Length_mm  INTEGER,
    TDP_W      INTEGER,
    VRAM_GB    INTEGER
);

CREATE TABLE PSU (
    PartID      INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Wattage     INTEGER,
    FormFactor  TEXT
);

-- Called PCCase because CASE is an SQL keyword
CREATE TABLE PCCase (
    PartID              INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    MaxGPULength_mm     INTEGER,
    MaxCoolerHeight_mm  INTEGER,
    PSUFormFactor       TEXT
);

CREATE TABLE Cooler (
    PartID     INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Height_mm  INTEGER
);

CREATE TABLE Storage (
    PartID       INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Interface    TEXT,
    Capacity_GB  INTEGER
);

-- Multi-valued attributes: one row per supported value
CREATE TABLE CaseFormFactor (
    PartID      INTEGER REFERENCES PCCase(PartID) ON DELETE CASCADE,
    FormFactor  TEXT NOT NULL,
    PRIMARY KEY (PartID, FormFactor)
);

CREATE TABLE CoolerSocket (
    PartID  INTEGER REFERENCES Cooler(PartID) ON DELETE CASCADE,
    Socket  TEXT NOT NULL,
    PRIMARY KEY (PartID, Socket)
);

-- Builds
CREATE TABLE Build (
    BuildID      INTEGER PRIMARY KEY,
    BuildName    TEXT NOT NULL,
    DateCreated  TEXT DEFAULT (date('now'))
);

CREATE TABLE BuildPart (
    BuildID  INTEGER REFERENCES Build(BuildID) ON DELETE CASCADE,
    PartID   INTEGER REFERENCES Part(PartID),
    PRIMARY KEY (BuildID, PartID)
);