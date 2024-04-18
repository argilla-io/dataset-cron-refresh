import os

import argilla as rg

REQUIRED_RESPONSES = int(os.environ["REQUIRED_RESPONSES"])
HF_TOKEN = os.environ["HF_TOKEN"]
languages = [
    "DUTCH",
    "SPANISH",
    "MALAGASY",
    "GERMAN",
    "SWAHILI",
    "FILIPINO",
    "ARABIC",
    "TAMIL",
    "CZECH",
    "HUNGARIAN",
]

dataset_info = [
    (
        language_,
        os.environ[f"ARGILLA_API_URL_{language_}"],
        os.environ[f"ARGILLA_API_KEY_{language_}"],
        os.environ[f"SOURCE_DATASET_{language_}"],
        os.environ[f"SOURCE_WORKSPACE_{language_}"],
        os.environ.get(
            f"RESULTS_DATASET_{language_}", os.environ[f"SOURCE_DATASET_{language_}"]
        ),
        os.environ.get(f"RESULTS_WORKSPACE_{language_}", "owner"),
    )
    for language_ in languages
]


def completed_with_overlap(records, required_responses):
    completed = []
    for r in records:
        if len(r.responses) >= required_responses:
            completed.append(r)
    return completed


for (
    language,
    api_url,
    api_key,
    SOURCE_DATASET,
    SOURCE_WS,
    RESULTS_DATASET,
    RESULTS_WS,
) in dataset_info:
    rg.init(api_url=api_url, api_key=api_key)

    # Create workspace if not present
    workspaces = rg.Workspace.list()
    workspace_presnt = any(workspace.name == RESULTS_WS for workspace in workspaces)
    if not workspace_presnt:
        rg.Workspace.create(RESULTS_WS)

    dataset = rg.FeedbackDataset.from_argilla(SOURCE_DATASET, workspace=SOURCE_WS)
    print(f"Current dataset size {language}: {len(dataset)} ")

    submitted_so_far = dataset.filter_by(response_status="submitted")
    print(f"Submitted {language}: {len(submitted_so_far)}")

    completed_remote_records = completed_with_overlap(
        submitted_so_far.records, REQUIRED_RESPONSES
    )
    print(f"Completed so far {language}: {len(completed_remote_records)}")

    if len(completed_remote_records) > 0:
        local_submitted = submitted_so_far.pull()
        completed_local_records = completed_with_overlap(
            local_submitted.records, REQUIRED_RESPONSES
        )
        try:
            results = rg.FeedbackDataset.from_argilla(
                RESULTS_DATASET, workspace=RESULTS_WS
            )
            try:
                results.add_records(completed_local_records)
                dataset.delete_records(list(completed_remote_records))
            except Exception as e:
                pass
        except Exception as e:
            results = local_submitted.push_to_argilla(
                RESULTS_DATASET, workspace=RESULTS_WS
            )
            dataset.delete_records(list(completed_remote_records))

        print(
            f"Updating private results with {len(completed_remote_records)} records {language}."
        )
        results.push_to_huggingface(f"DIBT/MPEP_{language}", token=HF_TOKEN)
