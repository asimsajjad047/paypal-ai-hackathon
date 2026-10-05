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

-- Subtype tables: one row per part of that type
CREATE TABLE CPU (
    PartID                INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Socket                TEXT NOT NULL,
    TDP_W                 INTEGER NOT NULL,
    HasIntegratedGraphics INTEGER NOT NULL CHECK (HasIntegratedGraphics IN (0,1)),
    Cores                 INTEGER,
    BoostClock            REAL
);

CREATE TABLE Motherboard (
    PartID      INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Socket      TEXT NOT NULL,
    FormFactor  TEXT NOT NULL,
    RAMType     TEXT NOT NULL,
    RAMSlots    INTEGER NOT NULL,
    MaxRAM_GB   INTEGER NOT NULL,
    M2Slots     INTEGER NOT NULL
);

CREATE TABLE RAM (
    PartID            INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    RAMType           TEXT NOT NULL,
    Speed_MHz         INTEGER,
    ModuleCount       INTEGER NOT NULL,
    TotalCapacity_GB  INTEGER NOT NULL
);

CREATE TABLE GPU (
    PartID     INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Length_mm  INTEGER NOT NULL,
    TDP_W      INTEGER NOT NULL,
    VRAM_GB    INTEGER
);

CREATE TABLE PSU (
    PartID      INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Wattage     INTEGER NOT NULL,
    FormFactor  TEXT NOT NULL
);

-- Called PCCase because CASE is an SQL keyword
CREATE TABLE PCCase (
    PartID              INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    MaxGPULength_mm     INTEGER NOT NULL,
    MaxCoolerHeight_mm  INTEGER NOT NULL,
    PSUFormFactor       TEXT NOT NULL
);

CREATE TABLE Cooler (
    PartID     INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Height_mm  INTEGER NOT NULL
);

CREATE TABLE Storage (
    PartID       INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Interface    TEXT NOT NULL,
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