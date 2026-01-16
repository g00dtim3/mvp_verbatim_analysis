-- ============================================================================
-- GIDA Reference Data - Version 2026.01
-- ============================================================================
-- Insert GIDA ontology entities and attributes
-- Run this SQL in Supabase SQL Editor after creating tables
-- ============================================================================

-- ============================================================================
-- 1. PATHOLOGIES (5 entities)
-- ============================================================================

INSERT INTO dim_ontology_entities
(id, ontology_version, entity_type, label, label_normalized, keywords, parent_id, is_active, created_at)
VALUES
  (
    gen_random_uuid(),
    '2026.01',
    'pathology',
    'Diabète',
    'diabete',
    '["diabète", "diabete", "glycémie", "insuline", "diabétique"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'pathology',
    'Hypertension',
    'hypertension',
    '["hypertension", "tension artérielle", "pression artérielle", "hypertendu"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'pathology',
    'Douleur',
    'douleur',
    '["douleur", "mal", "souffrance", "douloureux", "douloureuse"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'pathology',
    'Arthrose',
    'arthrose',
    '["arthrose", "articulation", "arthrosique", "rhumatisme"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'pathology',
    'Allergie',
    'allergie',
    '["allergie", "allergique", "réaction allergique", "hypersensibilité"]'::jsonb,
    NULL,
    true,
    NOW()
  );

-- ============================================================================
-- 2. BRANDS (5 entities)
-- ============================================================================

INSERT INTO dim_ontology_entities
(id, ontology_version, entity_type, label, label_normalized, keywords, parent_id, is_active, created_at)
VALUES
  (
    gen_random_uuid(),
    '2026.01',
    'brand',
    'Doliprane',
    'doliprane',
    '["doliprane", "paracétamol doliprane"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'brand',
    'Efferalgan',
    'efferalgan',
    '["efferalgan", "paracétamol efferalgan"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'brand',
    'Advil',
    'advil',
    '["advil", "ibuprofène advil"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'brand',
    'Spasfon',
    'spasfon',
    '["spasfon", "phloroglucinol"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'brand',
    'Actifed',
    'actifed',
    '["actifed", "pseudoéphédrine"]'::jsonb,
    NULL,
    true,
    NOW()
  );

-- ============================================================================
-- 3. ZONES (5 entities)
-- ============================================================================

INSERT INTO dim_ontology_entities
(id, ontology_version, entity_type, label, label_normalized, keywords, parent_id, is_active, created_at)
VALUES
  (
    gen_random_uuid(),
    '2026.01',
    'zone',
    'Tête',
    'tete',
    '["tête", "tete", "crâne", "céphalée", "migraine"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'zone',
    'Dos',
    'dos',
    '["dos", "colonne vertébrale", "lombaire", "dorsal"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'zone',
    'Genou',
    'genou',
    '["genou", "genoux", "rotule"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'zone',
    'Estomac',
    'estomac',
    '["estomac", "gastrique", "ventre", "abdomen"]'::jsonb,
    NULL,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'zone',
    'Gorge',
    'gorge',
    '["gorge", "pharynx", "mal de gorge", "angine"]'::jsonb,
    NULL,
    true,
    NOW()
  );

-- ============================================================================
-- 4. ATTRIBUTES (7 entities)
-- ============================================================================

INSERT INTO dim_ontology_attributes
(id, ontology_version, attribute_type, label, label_normalized, keywords, is_active, created_at)
VALUES
  (
    gen_random_uuid(),
    '2026.01',
    'attribute',
    'Efficacité',
    'efficacite',
    '["efficace", "efficacité", "fonctionne", "marche bien", "résultat"]'::jsonb,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'attribute',
    'Rapidité d''action',
    'rapidite_action',
    '["rapide", "rapidement", "vite", "immédiat", "en quelques minutes"]'::jsonb,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'attribute',
    'Tolérance',
    'tolerance',
    '["bien toléré", "tolérance", "sans effet secondaire", "supporte bien"]'::jsonb,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'attribute',
    'Prix',
    'prix',
    '["prix", "coût", "cher", "abordable", "économique", "bon marché"]'::jsonb,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'attribute',
    'Disponibilité',
    'disponibilite',
    '["disponible", "disponibilité", "facile à trouver", "en stock", "rupture"]'::jsonb,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'attribute',
    'Goût',
    'gout',
    '["goût", "gout", "saveur", "agréable", "désagréable", "amer"]'::jsonb,
    true,
    NOW()
  ),
  (
    gen_random_uuid(),
    '2026.01',
    'attribute',
    'Présentation',
    'presentation',
    '["comprimé", "gélule", "sirop", "suppositoire", "injection", "pommade"]'::jsonb,
    true,
    NOW()
  );

-- ============================================================================
-- Verification queries
-- ============================================================================

-- Check inserted entities
-- SELECT entity_type, COUNT(*)
-- FROM dim_ontology_entities
-- WHERE ontology_version = '2026.01'
-- GROUP BY entity_type;

-- Check inserted attributes
-- SELECT attribute_type, COUNT(*)
-- FROM dim_ontology_attributes
-- WHERE ontology_version = '2026.01'
-- GROUP BY attribute_type;

-- View all GIDA data
-- SELECT 'entity' as type, entity_type as subtype, label, keywords
-- FROM dim_ontology_entities
-- WHERE ontology_version = '2026.01'
-- UNION ALL
-- SELECT 'attribute' as type, attribute_type as subtype, label, keywords
-- FROM dim_ontology_attributes
-- WHERE ontology_version = '2026.01'
-- ORDER BY type, subtype, label;
