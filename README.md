# MediKong Services

FastAPI 기반 의료 MSA 서비스와 정적 dashboard를 개발하고 검증하는 repo입니다.

이 repo의 책임은 서비스 개발, 단위 테스트, Docker Compose E2E 테스트, Docker image build, registry push까지입니다. Kubernetes 배포 선언, Argo CD, Terraform, Ansible, Vagrant, 클러스터 운영 파일은 이 repo에 두지 않습니다.

## 구성

| 경로 | 내용 |
| --- | --- |
| `services/auth-service/` | 로그인, JWT 발급, 감사 로그 |
| `services/patient-service/` | 환자 정보와 의료 요약 |
| `services/appointment-service/` | 예약 요청, 확정, 취소와 예약 이벤트 발행 |
| `services/prescription-service/` | 처방 발행, 조회와 처방 이벤트 발행 |
| `services/notification-service/` | Kafka 이벤트 기반 알림 저장 |
| `dashboard/` | 서비스 동작을 확인하는 정적 화면 |
| `tests/` | Docker pytest runner와 Docker Compose E2E 테스트 |

## 테스트

로컬에는 Docker, Docker Compose, Make가 필요합니다. Python과 Newman은 컨테이너 안에서 실행합니다.

```bash
make test-unit
make test-e2e
```

`make test-unit`은 `tests/docker/Dockerfile`로 테스트 러너 이미지를 만든 뒤 각 서비스의 pytest를 실행합니다. `make test-e2e`는 PostgreSQL, MongoDB, Kafka, FastAPI 서비스를 Docker Compose로 올리고 Newman collection을 실행합니다.

## 이미지 빌드와 푸시

기본 registry는 로컬 lab registry인 `10.10.10.10:5000`입니다.

```bash
make app-images-build IMAGE_TAG=dev-split-smoke
make app-images-push IMAGE_TAG=dev-split-smoke
```

외부 registry로 바꿀 때는 `IMAGE_REGISTRY`, 필요하면 `IMAGE_NAMESPACE`를 지정합니다.

```bash
IMAGE_REGISTRY=ghcr.io IMAGE_NAMESPACE=owner/service make app-images-push IMAGE_TAG=dev
```

## 제외 범위

다음 책임은 별도 배포/인프라 repo에서 다룹니다.

- Kubernetes manifests, Kustomize overlays, NetworkPolicy, HPA, PDB
- Argo CD Application과 GitOps sync
- Terraform, Ansible, Vagrant, kubeadm cluster 운영
- registry bootstrap, VM bootstrap, cluster apply

자세한 테스트 흐름은 `tests/README.md`를 참고합니다.
