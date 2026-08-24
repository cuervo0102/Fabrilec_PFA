with docs as (
    select * from {{ ref('stg_raw_documents') }}
),

summary as (
    select
        tender_ref,
        count(*) as n_documents,
        count(*) filter (where extraction_quality = 'fiable') as n_fiable,
        count(*) filter (where extraction_quality = 'ocr_a_verifier') as n_ocr_a_verifier,
        count(*) filter (where extraction_quality = 'echec') as n_echec,
        sum(char_count) as total_chars,
        bool_or(document_type = 'CCTP') as has_cctp,
        bool_or(document_type = 'CPS') as has_cps,
        bool_or(document_type = 'RC') as has_rc,
        bool_or(document_type = 'BORDEREAU_PRIX') as has_bordereau_prix,
        max(loaded_at) as last_loaded_at
    from docs
    group by tender_ref
)

select * from summary