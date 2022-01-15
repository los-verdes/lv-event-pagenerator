py_dir := "events_page"
tf_dir := "terraform"
tfvars_file := "losverdesatx-events.tfvars"


tf-init:
  terraform -chdir="{{ tf_dir }}" init

run-tf command: tf-init
    terraform -chdir="{{ tf_dir }}" {{ command }} -var-file='../{{ tfvars_file }}'

tf-auto-apply:
  just run-tf plan
  just run-tf 'apply -auto-approve'

set-tf-ver-output:
  echo "::set-output name=terraform_version::$(cat ./.terraform-version)"


run-py command:
  cd "{{ py_dir }}" && {{ command }}

install-python-reqs:
  just run-py 'pip3 install --requirement=requirements.txt --quiet'

ensure-watches: install-python-reqs
  just run-py './ensure_watches.py --quiet'

dispatch-build-run: install-python-reqs
  just run-py './dispatch_build_workflow_run.py  --quiet'

build-and-publish: install-python-reqs
  just run-py './build_and_publish_site.py --quiet'

serve:
  just run-py './render_templated_styles.py'
  just run-py './app.py'
