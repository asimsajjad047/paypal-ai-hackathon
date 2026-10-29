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
    DateListed   TEXT DEFAULT (date('now')),
    Source       TEXT NOT NULL DEFAULT 'test',   -- 'test', 'channel3' or 'ebay'
    ExternalID   TEXT,                           -- the listing's ID on that website
    URL          TEXT,                           -- link to the real listing
    LastSeen     TEXT DEFAULT (date('now')),     -- last time the fetcher saw it
    UNIQUE (Source, ExternalID)                  -- lets the fetcher update instead of duplicate
);

-- One row per part per day: the cheapest price we saw. Feeds the buy/wait rating.
CREATE TABLE PriceHistory (
    PartID     INTEGER NOT NULL REFERENCES Part(PartID) ON DELETE CASCADE,
    Date       TEXT NOT NULL,
    Price      REAL NOT NULL CHECK (Price > 0),
    Condition  TEXT NOT NULL DEFAULT 'New' CHECK (Condition IN ('New','Used')),
    Source     TEXT NOT NULL DEFAULT 'test',
    PRIMARY KEY (PartID, Date, Condition, Source)
);

-- ============ BUILDS (what RigAgent puts together) ============

CREATE TABLE Build (
    BuildID       INTEGER PRIMARY KEY,
    BuildName     TEXT NOT NULL,
    Budget        REAL CHECK (Budget > 0),
    Requirements  TEXT,                -- JSON text, e.g. games, resolution, new/used
    TotalPrice    REAL CHECK (TotalPrice >= 0),
    Status        TEXT NOT NULL DEFAULT 'Draft'
                  CHECK (Status IN ('Draft','Approved','Paid','Cancelled','Refunded')),
    DateCreated   TEXT DEFAULT (date('now'))
);

CREATE TABLE BuildItem (
    BuildID    INTEGER NOT NULL REFERENCES Build(BuildID) ON DELETE CASCADE,
    ListingID  INTEGER NOT NULL REFERENCES Listing(ListingID),   -- now a LISTING, not a part
    Quantity   INTEGER NOT NULL DEFAULT 1 CHECK (Quantity > 0),  -- fixes "2 identical SSDs"
    AgreedPrice REAL CHECK (AgreedPrice > 0),   -- price after negotiation (NULL = listed price)
    PRIMARY KEY (BuildID, ListingID)
);

-- ============ PAYMENTS (PayPal) ============

-- One row per PayPal order (one checkout = one order, however many sellers)
CREATE TABLE PayPalOrder (
    OrderID      TEXT PRIMARY KEY,            -- PayPal's order ID (or MOCK-... offline)
    BuildID      INTEGER NOT NULL REFERENCES Build(BuildID) ON DELETE CASCADE,
    Mode         TEXT NOT NULL CHECK (Mode IN ('marketplace','split','mock')),
    Status       TEXT NOT NULL DEFAULT 'CREATED',  -- CREATED, APPROVED, COMPLETED, ...
    Total        REAL NOT NULL,
    Currency     TEXT NOT NULL DEFAULT 'GBP',
    ApprovalURL  TEXT,
    CaptureID    TEXT,                        -- marketplace mode: the single capture
    DateCreated  TEXT DEFAULT (datetime('now')),
    DateUpdated  TEXT DEFAULT (datetime('now'))
);

-- What each seller is owed from an order, and what happened to that money
CREATE TABLE SellerPayment (
    PaymentID    INTEGER PRIMARY KEY,
    OrderID      TEXT NOT NULL REFERENCES PayPalOrder(OrderID) ON DELETE CASCADE,
    SellerID     INTEGER NOT NULL REFERENCES Seller(SellerID),
    Amount       REAL NOT NULL CHECK (Amount > 0),
    Escrow       INTEGER NOT NULL DEFAULT 0 CHECK (Escrow IN (0,1)),  -- 1 = used part, held
    Status       TEXT NOT NULL DEFAULT 'Pending'
                 CHECK (Status IN ('Pending','Held','Paid','Refunded','Failed')),
    PayPalRef    TEXT,                        -- capture ID, payout batch ID or refund ID
    Note         TEXT
);

-- ============ AGENT HISTORY ============

CREATE TABLE Negotiation (
    NegotiationID  INTEGER PRIMARY KEY,
    ListingID      INTEGER NOT NULL REFERENCES Listing(ListingID) ON DELETE CASCADE,
    AskingPrice    REAL NOT NULL,
    MaxPrice       REAL NOT NULL,             -- buyer's hard limit
    FinalPrice     REAL,                      -- NULL = no deal
    Outcome        TEXT NOT NULL CHECK (Outcome IN ('Deal','NoDeal')),
    Transcript     TEXT NOT NULL,             -- JSON list of messages
    DateCreated    TEXT DEFAULT (datetime('now'))
);

-- Price watch: "buy this part if it drops to £X" (auto-buy)
CREATE TABLE Watch (
    WatchID      INTEGER PRIMARY KEY,
    PartID       INTEGER NOT NULL REFERENCES Part(PartID) ON DELETE CASCADE,
    TargetPrice  REAL NOT NULL CHECK (TargetPrice > 0),
    MaxPrice     REAL NOT NULL CHECK (MaxPrice >= TargetPrice),  -- pre-approved spending limit
    AllowUsed    INTEGER NOT NULL DEFAULT 0 CHECK (AllowUsed IN (0,1)),
    Status       TEXT NOT NULL DEFAULT 'Watching'
                 CHECK (Status IN ('Watching','Triggered','Bought','Cancelled')),
    OrderID      TEXT,                        -- PayPal order created when triggered
    DateCreated  TEXT DEFAULT (datetime('now'))
);