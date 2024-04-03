import os
import argilla as rg

# this is where annotators will do annotations
SOURCE_DATASET = "prompts"
SOURCE_WS = "dibt"
# this is a restricted workspace
# where admins/owners will store the annotations
# no annotator has access
RESULTS_DATASET = "results"
RESULTS_WS = "admin"

rg.init(
    api_url=os.getenv("ARGILLA_API_URL"),
    api_key=os.getenv("ARGILLA_API_KEY")
)

def completed_with_overlap(records, min_overlap=2):
  completed = []
  for r in records:
      if len(r.responses)>=2:
        completed.append(r)
  return completed

dataset = rg.FeedbackDataset.from_argilla(SOURCE_DATASET, workspace=SOURCE_WS)
print(f"Current dataset size: {len(dataset)}")

submitted_so_far = dataset.filter_by(response_status="submitted")
print(f"Submitted: {len(submitted_so_far)}")

completed_remote_records = completed_with_overlap(submitted_so_far.records)
print(f"Completed so far: {len(completed_remote_records)}")

if len(completed_remote_records)>0:
  local_submitted = submitted_so_far.pull()
  completed_local_records = completed_with_overlap(local_submitted.records)
  try:
    print(f"Updating private results with {len(completed_remote_records)} records.")
    results = rg.FeedbackDataset.from_argilla(RESULTS_DATASET, workspace=RESULTS_WS)
    results.add_records(completed_local_records)
    results.push_to_huggingface("argilla/prompt-collective", token=os.getenv("HF_TOKEN"))
  except:
    local_submitted.push_to_argilla(RESULTS_DATASET, workspace=RESULTS_WS)

  dataset.delete_records(list(completed_remote_records))
