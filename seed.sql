PRAGMA foreign_keys = ON;

-- ===== PARTS (general info) =====
INSERT INTO Part (PartID, Name, Brand, Category) VALUES
 (1,  'Ryzen 5 7600',            'AMD',          'CPU'),
 (2,  'Core i5-12400F',          'Intel',        'CPU'),
 (3,  'B650 Tomahawk WiFi',      'MSI',          'Motherboard'),
 (4,  'PRO B760M-A DDR4',        'MSI',          'Motherboard'),
 (5,  'Vengeance DDR5 32GB',     'Corsair',      'RAM'),
 (6,  'Vengeance LPX DDR4 16GB', 'Corsair',      'RAM'),
 (7,  'RTX 4070',                'NVIDIA',       'GPU'),
 (8,  'RM750e',                  'Corsair',      'PSU'),
 (9,  'H5 Flow',                 'NZXT',         'Case'),
 (10, 'Peerless Assassin 120 SE','Thermalright', 'Cooler'),
 (11, '990 Pro 1TB',             'Samsung',      'Storage');

-- ===== DETAILS FOR EACH PART TYPE =====
INSERT INTO CPU (PartID, Socket, TDP_W, HasIntegratedGraphics, Cores, BoostClock, BenchmarkScore) VALUES
 (1, 'AM5',     65, 1, 6, 5.1, 27000),
 (2, 'LGA1700', 65, 0, 6, 4.4, 19500);

INSERT INTO Motherboard (PartID, Socket, FormFactor, RAMType, RAMSlots, MaxRAM_GB, M2Slots) VALUES
 (3, 'AM5',     'ATX',       'DDR5', 4, 192, 3),
 (4, 'LGA1700', 'Micro-ATX', 'DDR4', 4, 128, 2);

INSERT INTO RAM (PartID, RAMType, Speed_MHz, ModuleCount, TotalCapacity_GB) VALUES
 (5, 'DDR5', 6000, 2, 32),
 (6, 'DDR4', 3200, 2, 16);

INSERT INTO GPU (PartID, Length_mm, TDP_W, VRAM_GB, BenchmarkScore) VALUES
 (7, 244, 200, 12, 26900);

INSERT INTO PSU (PartID, Wattage, FormFactor) VALUES
 (8, 750, 'ATX');

INSERT INTO PCCase (PartID, MaxGPULength_mm, MaxCoolerHeight_mm, PSUFormFactor) VALUES
 (9, 365, 165, 'ATX');

INSERT INTO CaseFormFactor (PartID, FormFactor) VALUES
 (9, 'ATX'),
 (9, 'Micro-ATX'),
 (9, 'Mini-ITX');

INSERT INTO Cooler (PartID, Height_mm) VALUES
 (10, 155);

INSERT INTO CoolerSocket (PartID, Socket) VALUES
 (10, 'AM4'),
 (10, 'AM5'),
 (10, 'LGA1700');

INSERT INTO Storage (PartID, Interface, Capacity_GB) VALUES
 (11, 'M.2 NVMe', 1000);

-- ===== SELLERS =====
INSERT INTO Seller (SellerID, Name, PayPalEmail, SellerType, MinPriceFactor) VALUES
 (1, 'PartsCo',      'partsco@business.example.com',   'Shop',       1.00),
 (2, 'TechDeals',    'techdeals@business.example.com', 'Shop',       1.00),
 (3, 'Dave (used)',  'dave@business.example.com',      'Individual', 0.85),
 (4, 'Priya (used)', 'priya@business.example.com',     'Individual', 0.90);

-- ===== LISTINGS (test data - real web prices come later) =====
INSERT INTO Listing (ListingID, PartID, SellerID, Condition, Price) VALUES
 (1,  1,  1, 'New', 199),
 (2,  2,  1, 'New', 129),
 (3,  3,  2, 'New', 189),
 (4,  4,  2, 'New', 119),
 (5,  5,  1, 'New',  95),
 (6,  6,  1, 'New',  39),
 (7,  7,  2, 'New', 549),
 (8,  8,  1, 'New',  89),
 (9,  9,  2, 'New',  89),
 (10, 10, 1, 'New',  35),
 (11, 11, 2, 'New',  99),
 (12, 7,  1, 'New', 539),
 (13, 7,  3, 'Used', 380),
 (14, 1,  4, 'Used', 150),
 (15, 5,  3, 'Used',  70);

 -- ===== DELIBERATELY "PROBLEM" PARTS FOR TESTING =====
INSERT INTO Part (PartID, Name, Brand, Category) VALUES
 (12, 'RTX 4090 Gaming OC', 'Gigabyte',      'GPU'),   -- very long, very power hungry
 (13, 'MWE 450 Bronze V2',  'Cooler Master', 'PSU'),   -- weak PSU
 (14, 'NR200P',             'Cooler Master', 'Case');  -- small Mini-ITX case

INSERT INTO GPU (PartID, Length_mm, TDP_W, VRAM_GB, BenchmarkScore) VALUES
 (12, 340, 450, 24, 38000);

INSERT INTO PSU (PartID, Wattage, FormFactor) VALUES
 (13, 450, 'ATX');

INSERT INTO PCCase (PartID, MaxGPULength_mm, MaxCoolerHeight_mm, PSUFormFactor) VALUES
 (14, 330, 155, 'SFX');

INSERT INTO CaseFormFactor (PartID, FormFactor) VALUES
 (14, 'Mini-ITX');

INSERT INTO Listing (ListingID, PartID, SellerID, Condition, Price) VALUES
 (16, 12, 2, 'New', 1699),
 (17, 13, 1, 'New',   45),
 (18, 14, 2, 'New',   99);