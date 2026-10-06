PRAGMA foreign_keys = ON;

-- ============ PARTS (what a part IS) ============

CREATE TABLE Part (
    PartID    INTEGER PRIMARY KEY,
    Name      TEXT NOT NULL,
    Brand     TEXT NOT NULL,
    Category  TEXT NOT NULL CHECK (Category IN
              ('CPU','Motherboard','RAM','GPU','PSU','Case','Cooler','Storage'))
    -- Price removed: it now lives in Listing
);

CREATE TABLE CPU (
    PartID                INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Socket                TEXT NOT NULL CHECK (Socket IN ('AM4','AM5','LGA1700','LGA1851')),
    TDP_W                 INTEGER NOT NULL CHECK (TDP_W > 0),
    HasIntegratedGraphics INTEGER NOT NULL CHECK (HasIntegratedGraphics IN (0,1)),
    Cores                 INTEGER,
    BoostClock            REAL,
    BenchmarkScore        INTEGER NOT NULL CHECK (BenchmarkScore > 0)   -- NEW
);

CREATE TABLE Motherboard (
    PartID      INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Socket      TEXT NOT NULL CHECK (Socket IN ('AM4','AM5','LGA1700','LGA1851')),
    FormFactor  TEXT NOT NULL CHECK (FormFactor IN ('ATX','Micro-ATX','Mini-ITX')),
    RAMType     TEXT NOT NULL CHECK (RAMType IN ('DDR4','DDR5')),
    RAMSlots    INTEGER NOT NULL,
    MaxRAM_GB   INTEGER NOT NULL,
    M2Slots     INTEGER NOT NULL
);

CREATE TABLE RAM (
    PartID            INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    RAMType           TEXT NOT NULL CHECK (RAMType IN ('DDR4','DDR5')),
    Speed_MHz         INTEGER,
    ModuleCount       INTEGER NOT NULL,
    TotalCapacity_GB  INTEGER NOT NULL
);

CREATE TABLE GPU (
    PartID          INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Length_mm       INTEGER NOT NULL,
    TDP_W           INTEGER NOT NULL CHECK (TDP_W > 0),
    VRAM_GB         INTEGER,
    BenchmarkScore  INTEGER NOT NULL CHECK (BenchmarkScore > 0)   -- NEW
);

CREATE TABLE PSU (
    PartID      INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Wattage     INTEGER NOT NULL CHECK (Wattage > 0),
    FormFactor  TEXT NOT NULL CHECK (FormFactor IN ('ATX','SFX'))
);

CREATE TABLE PCCase (
    PartID              INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    MaxGPULength_mm     INTEGER NOT NULL,
    MaxCoolerHeight_mm  INTEGER NOT NULL,
    PSUFormFactor       TEXT NOT NULL CHECK (PSUFormFactor IN ('ATX','SFX'))
);

CREATE TABLE Cooler (
    PartID     INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Height_mm  INTEGER NOT NULL
);

CREATE TABLE Storage (
    PartID       INTEGER PRIMARY KEY REFERENCES Part(PartID) ON DELETE CASCADE,
    Interface    TEXT NOT NULL CHECK (Interface IN ('M.2 NVMe','SATA')),
    Capacity_GB  INTEGER
);

CREATE TABLE CaseFormFactor (
    PartID      INTEGER REFERENCES PCCase(PartID) ON DELETE CASCADE,
    FormFactor  TEXT NOT NULL CHECK (FormFactor IN ('ATX','Micro-ATX','Mini-ITX')),
    PRIMARY KEY (PartID, FormFactor)
);

CREATE TABLE CoolerSocket (
    PartID  INTEGER REFERENCES Cooler(PartID) ON DELETE CASCADE,
    Socket  TEXT NOT NULL CHECK (Socket IN ('AM4','AM5','LGA1700','LGA1851')),
    PRIMARY KEY (PartID, Socket)
);

-- ============ SELLING (where to buy it, and for how much) ============

CREATE TABLE Seller (
    SellerID        INTEGER PRIMARY KEY,
    Name            TEXT NOT NULL,
    PayPalEmail     TEXT NOT NULL UNIQUE,          -- the seller's SANDBOX business email
    SellerType      TEXT NOT NULL CHECK (SellerType IN ('Shop','Individual')),
    MinPriceFactor  REAL NOT NULL DEFAULT 1.0
                    CHECK (MinPriceFactor > 0 AND MinPriceFactor <= 1)
                    -- for negotiation later: 0.85 = will accept down to 85% of listed price
);

CREATE TABLE Listing (
    ListingID    INTEGER PRIMARY KEY,
    PartID       INTEGER NOT NULL REFERENCES Part(PartID) ON DELETE CASCADE,
    SellerID     INTEGER NOT NULL REFERENCES Seller(SellerID) ON DELETE CASCADE,
    Condition    TEXT NOT NULL CHECK (Condition IN ('New','Used')),
    Price        REAL NOT NULL CHECK (Price > 0),
    DateListed   TEXT DEFAULT (date('now'))
);

-- ============ BUILDS (what RigAgent puts together) ============

CREATE TABLE Build (
    BuildID       INTEGER PRIMARY KEY,
    BuildName     TEXT NOT NULL,
    Budget        REAL CHECK (Budget > 0),
    Requirements  TEXT,                -- JSON text, e.g. games, resolution, new/used
    TotalPrice    REAL CHECK (TotalPrice >= 0),
    Status        TEXT NOT NULL DEFAULT 'Draft'
                  CHECK (Status IN ('Draft','Approved','Paid','Cancelled')),
    DateCreated   TEXT DEFAULT (date('now'))
);

CREATE TABLE BuildItem (
    BuildID    INTEGER NOT NULL REFERENCES Build(BuildID) ON DELETE CASCADE,
    ListingID  INTEGER NOT NULL REFERENCES Listing(ListingID),   -- now a LISTING, not a part
    Quantity   INTEGER NOT NULL DEFAULT 1 CHECK (Quantity > 0),  -- fixes "2 identical SSDs"
    PRIMARY KEY (BuildID, ListingID)
);