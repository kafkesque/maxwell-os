{
  "run_a": "idem_a",
  "run_b": "idem_b",
  "corpus_confound": false,
  "stage_report": [
    {
      "stage": "stage0_convert.py",
      "count_a": 16,
      "count_b": 16,
      "identical": true,
      "digest_stats": {
        "a": 16,
        "b": 16,
        "intersection": 16,
        "a_only": 0,
        "b_only": 0,
        "jaccard": 1.0
      }
    },
    {
      "stage": "stage0_5_extract_metadata.py",
      "count_a": 0,
      "count_b": 0,
      "identical": true,
      "digest_stats": {
        "a": 0,
        "b": 0,
        "intersection": 0,
        "a_only": 0,
        "b_only": 0,
        "jaccard": 0.0
      }
    },
    {
      "stage": "stage1_chunk.py",
      "count_a": 6746,
      "count_b": 6746,
      "identical": true,
      "digest_stats": {
        "a": 6746,
        "b": 6746,
        "intersection": 6746,
        "a_only": 0,
        "b_only": 0,
        "jaccard": 1.0
      }
    },
    {
      "stage": "stage1_3_prefilter.py",
      "count_a": 1,
      "count_b": 1,
      "identical": true,
      "digest_stats": {
        "a": 1,
        "b": 1,
        "intersection": 1,
        "a_only": 0,
        "b_only": 0,
        "jaccard": 1.0
      }
    },
    {
      "stage": "stage1_5_embed_cluster.py",
      "count_a": 699,
      "count_b": 699,
      "identical": true,
      "digest_stats": {
        "a": 699,
        "b": 699,
        "intersection": 699,
        "a_only": 0,
        "b_only": 0,
        "jaccard": 1.0
      }
    },
    {
      "stage": "stage2_extract.py",
      "count_a": 521,
      "count_b": 521,
      "identical": false,
      "digest_stats": {
        "a": 521,
        "b": 521,
        "intersection": 1,
        "a_only": 520,
        "b_only": 520,
        "jaccard": 0.001
      }
    },
    {
      "stage": "stage4_merge.py",
      "count_a": 463,
      "count_b": 466,
      "identical": false,
      "digest_stats": {
        "a": 463,
        "b": 466,
        "intersection": 0,
        "a_only": 463,
        "b_only": 466,
        "jaccard": 0.0
      }
    },
    {
      "stage": "stage5_verify.py",
      "count_a": 463,
      "count_b": 466,
      "identical": false,
      "digest_stats": {
        "a": 463,
        "b": 466,
        "intersection": 0,
        "a_only": 463,
        "b_only": 466,
        "jaccard": 0.0
      }
    }
  ],
  "s5": {
    "metrics": {
      "fb_id": {
        "a": 463,
        "b": 466,
        "intersection": 199,
        "a_only": 264,
        "b_only": 267,
        "jaccard": 0.2726
      },
      "name": {
        "a": 463,
        "b": 466,
        "intersection": 389,
        "a_only": 74,
        "b_only": 77,
        "jaccard": 0.7204
      },
      "body_hash_8field": {
        "a": 463,
        "b": 466,
        "intersection": 0,
        "a_only": 463,
        "b_only": 466,
        "jaccard": 0.0
      },
      "shared_name_identical_definition": 199,
      "shared_name_different_definition": 190
    },
    "present": true
  }
}
