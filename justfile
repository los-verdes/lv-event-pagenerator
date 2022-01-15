py_dir      := "events_page"
tfvars_file := "losverdesatx-events.tfvars"
tf_subdir   := "./terraform"

set-tf-ver-output:
  echo "::set-output name=terraform_version::$(cat {{ tf_subdir }}/.terraform-version)"

run-tf CMD:
  terraform -chdir="{{ justfile_directory() + "/" + tf_subdir }}" \
    {{ CMD }} \
    {{ if CMD != "init" { "-var-file=../" + tfvars_file } else { "" } }}

tf-init:
  just run-tf init

tf-auto-apply: tf-init
  just run-tf 'apply -auto-approve'

run-py +command:
  # export EVENTS_PAGE_SA_EMAIL="$(terraform -chdir=terraform output -raw site_publisher_sa_email)"
  cd "{{ py_dir }}" && {{ command }}

install-python-reqs:
  just run-py 'pip3 install --requirement=requirements.txt --quiet'

ensure-watches: install-python-reqs
  just run-py './ensure_watches.py --quiet'

dispatch-build-run: install-python-reqs
  just run-py './dispatch_build_workflow_run.py  --quiet'

build-and-publish: install-python-reqs
  just run-py './build_and_publish_site.py --quiet'

cleanup-test-site-prefix: install-python-reqs
  just run-py './remove_subpath_from_gcs.py --quiet'

serve:
  just run-py './render_templated_styles.py'
  just run-py './app.py'
