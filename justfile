
set dotenv-load := true

# alias template-sites := template-styles-from-drive-settings

tfvars_file := "losverdesatx-events.tfvars"
tf_dir := "terraform"
py_dir := "events_page"



run-tf command:
    terraform -chdir="{{ tf_dir }}" {{ command }} -var-file='../{{ tfvars_file }}'

tf-init:
  #!/bin/bash
  if [[ ! -d "{{ tf_dir }}/.terraform" ]]
  then
    terraform -chdir="{{ tf_dir }}" init
  fi

tf-plan: tf-init
  just run-tf plan

tf-apply:
  just run-tf apply

tf-auto-apply: tf-plan
  just run-tf 'apply -auto-approve'

tf-targeted-apply target:
  just run-tf 'apply -auto-approve -target={{ target }}'

tf-unlock lock_id:
  just run-tf "force-unlock -force '{{ lock_id }}'"

set-tf-ver-output:
  echo "::set-output name=terraform_version::$(cat ./.terraform-version)"

export-env: tf-init
  just tf-targeted-apply 'local_file.dotenv'

render-templated-styles:
  cd "{{ py_dir }}" && ./render_templated_styles.py

install-python-reqs:
  cd "{{ py_dir }}" && pip3 install --requirement=requirements.txt

build-and-publish: install-python-reqs render-templated-styles
  echo "build-and-publish"
  cd "{{ py_dir }}" && ./build_and_publish_site.py
  # --quiet

# serve: install-python-reqs export-env render-templated-styles
serve: render-templated-styles
  cd "{{ py_dir }}" && ./app.py

ensure-watches: install-python-reqs
  ./event_page/ensure_watches.py

dispatch-build-run: install-python-reqs
  cd "{{ py_dir }}" && ./dispatch_build_workflow_run.py
