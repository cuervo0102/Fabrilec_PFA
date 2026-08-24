with source as (
    select * from {{ source('fabrilec', 'raw_documents') }}
),

classified as (
    select
        id,
        tender_ref,
        relative_path,
        source_path,
        extension,
        extraction_method,
        char_count,
        n_pages,
        error,
        loaded_at,

       
        case
            when relative_path ilike '%CCTP%' then 'CCTP'
            when relative_path ilike '%CCAG%' then 'CCAG'
            when relative_path ilike '%CPS%' then 'CPS'
            when relative_path ilike '%reglement%' or relative_path ilike '%règlement%' or relative_path ilike '%RC%' then 'RC'
            when relative_path ilike '%bordereau%' or relative_path ilike '%BPDE%' then 'BORDEREAU_PRIX'
            when relative_path ilike '%avis%' then 'AVIS'
            when relative_path ilike '%acte d%engagement%' then 'ACTE_ENGAGEMENT'
            when relative_path ilike '%declaration%honneur%' or relative_path ilike '%déclaration%honneur%' then 'DECLARATION_HONNEUR'
            when relative_path ilike '%plan de charge%' then 'PLAN_DE_CHARGE'
            else 'AUTRE'
        end as document_type,

        
        case
            when error is not null or char_count = 0
                or extraction_method in ('error', 'doc_conversion_failed', 'unsupported')
                then 'echec'
            when extraction_method = 'ocr' then 'ocr_a_verifier'
            else 'fiable'
        end as extraction_quality

    from source
)

select * from classified