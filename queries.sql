-- =====================================================
-- RigAgent: compatibility rule queries
-- Run with: sqlite3 -header -column pcparts.db < queries.sql
-- =====================================================


-- 1. Which motherboards fit the Ryzen 5 7600? (socket must match)
SELECT cpuPart.Name   AS CPU,
       mbPart.Name    AS Motherboard,
       c.Socket       AS Socket
FROM CPU c
JOIN Part cpuPart   ON cpuPart.PartID = c.PartID
JOIN Motherboard m  ON m.Socket = c.Socket          -- the compatibility rule
JOIN Part mbPart    ON mbPart.PartID = m.PartID
WHERE c.PartID = 1;


-- 2. Which RAM works with the B650 Tomahawk? (RAM type must match)
SELECT mbPart.Name   AS Motherboard,
       ramPart.Name  AS RAM,
       r.RAMType     AS RAMType
FROM Motherboard m
JOIN Part mbPart   ON mbPart.PartID = m.PartID
JOIN RAM r         ON r.RAMType = m.RAMType          -- the compatibility rule
JOIN Part ramPart  ON ramPart.PartID = r.PartID
WHERE m.PartID = 3;


-- 3. Does the RTX 4070 fit in the H5 Flow? (GPU length vs case clearance)
SELECT gpuPart.Name          AS GPU,
       casePart.Name         AS PCCase,
       g.Length_mm           AS GPULength,
       pc.MaxGPULength_mm    AS MaxAllowed,
       CASE WHEN g.Length_mm <= pc.MaxGPULength_mm
            THEN 'Fits' ELSE 'Too long' END AS Result
FROM GPU g
JOIN Part gpuPart   ON gpuPart.PartID = g.PartID
CROSS JOIN PCCase pc
JOIN Part casePart  ON casePart.PartID = pc.PartID
WHERE g.PartID = 7 AND pc.PartID = 9;


-- 4. Is the RM750e powerful enough for Ryzen 5 7600 + RTX 4070?
--    Rule: (CPU watts + GPU watts) x 1.2 headroom <= PSU wattage
SELECT c.TDP_W                         AS CPU_W,
       g.TDP_W                         AS GPU_W,
       (c.TDP_W + g.TDP_W) * 1.2       AS Needed_W,
       p.Wattage                       AS PSU_W,
       CASE WHEN (c.TDP_W + g.TDP_W) * 1.2 <= p.Wattage
            THEN 'Enough' ELSE 'Too weak' END AS Result
FROM CPU c
CROSS JOIN GPU g
CROSS JOIN PSU p
WHERE c.PartID = 1 AND g.PartID = 7 AND p.PartID = 8;


-- 5. Cheapest listing for each part, with seller and condition
--    (SQLite returns the seller/condition from the row with the MIN price)
SELECT p.Name           AS Part,
       p.Category       AS Category,
       MIN(l.Price)     AS CheapestPrice,
       s.Name           AS Seller,
       l.Condition      AS Condition
FROM Listing l
JOIN Part p    ON p.PartID = l.PartID
JOIN Seller s  ON s.SellerID = l.SellerID
GROUP BY p.PartID
ORDER BY p.PartID;


-- 6. Does the Peerless Assassin cooler fit the Ryzen 5 7600 AND the H5 Flow case?
--    Rule A: cooler supports the CPU's socket
--    Rule B: cooler height <= case max cooler height
SELECT coolerPart.Name  AS Cooler,
       CASE WHEN EXISTS (SELECT 1 FROM CoolerSocket cs
                         WHERE cs.PartID = k.PartID AND cs.Socket = c.Socket)
            THEN 'Yes' ELSE 'No' END             AS SocketOK,
       k.Height_mm                               AS CoolerHeight,
       pc.MaxCoolerHeight_mm                     AS MaxAllowed,
       CASE WHEN k.Height_mm <= pc.MaxCoolerHeight_mm
            THEN 'Yes' ELSE 'No' END             AS HeightOK
FROM Cooler k
JOIN Part coolerPart ON coolerPart.PartID = k.PartID
CROSS JOIN CPU c
CROSS JOIN PCCase pc
WHERE k.PartID = 10 AND c.PartID = 1 AND pc.PartID = 9;


-- 7. Does each motherboard fit in the H5 Flow? (form factor must be supported)
SELECT mbPart.Name    AS Motherboard,
       m.FormFactor   AS FormFactor,
       CASE WHEN EXISTS (SELECT 1 FROM CaseFormFactor cf
                         WHERE cf.PartID = 9 AND cf.FormFactor = m.FormFactor)
            THEN 'Fits' ELSE 'Does not fit' END AS Result
FROM Motherboard m
JOIN Part mbPart ON mbPart.PartID = m.PartID;