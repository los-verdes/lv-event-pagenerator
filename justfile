
set dotenv-load := true
py_dir := "events_page"
tf_dir := "terraform"


tf-init:
  #!/bin/bash
  if [[ ! -d "{{ tf_dir }}/.terraform" ]]
  then
    terraform -chdir="{{ tf_dir }}" init
  fi

tf-plan: tf-init
  terraform -chdir="{{ tf_dir }}" plan

tf-apply: tf-plan
  terraform -chdir="{{ tf_dir }}" apply

tf-auto-apply: tf-plan
  terraform -chdir="{{ tf_dir }}" apply -auto-approve


export-env: tf-init
  #!/bin/bash
  > .env
  EVENTS_PAGE_ENV="$(terraform -chdir=terraform output -json events_page_env)"
  while read -rd $'' line
  do
      export "$line"
      echo "$line" >> .env
  done < <(jq -r <<<"$EVENTS_PAGE_ENV" \
          'to_entries|map("\(.key)=\(.value)\u0000")[]')

install-python-reqs:
  cd "{{ py_dir }}" && pip3 install --requirement=requirements.txt

build-and-publish: export-env install-python-reqs
  echo "build-and-publish"
  cd "{{ py_dir }}" && ./build_and_publish_site.py
  # --quiet

ensure-watches: export-env
  ./event_page/ensure_watches.py
