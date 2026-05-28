# AGENTS.md

이 repo는 서비스 코드, 테스트, OpenAPI 계약, Docker image build, registry push workflow를 담당한다. 배포 선언, Argo CD, Terraform, Ansible, 클러스터 운영 파일은 sibling `gitops` 또는 `infra` repo에서 다룬다.

서비스를 추가하거나 수정할 때는 공통 서비스 계약을 함께 유지한다: `/healthz`, `/readyz`, `/metrics`, OpenAPI 문서, Dockerfile, unit test, integration test, structured JSON log.
