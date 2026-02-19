"""Deploy Recruitee MCP Server to GCP Cloud Run"""
import pulumi
import pulumi_gcp as gcp
import pulumi_docker as docker

# Get configuration
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
project_id = gcp_config.require("project")
region = gcp_config.get("region") or "europe-west2"

# Get required secrets from Pulumi config
recruitee_company_id = config.require_secret("recruitee_company_id")
recruitee_api_token = config.require_secret("recruitee_api_token")
documents_dir = config.get("documents_dir") or "/data/documents"

# OAuth2 configuration (optional) - FastMCP OAuth Proxy
# Note: FastMCP handles redirect URIs automatically using BASE_DEPLOY_URL
google_oauth_client_id = config.get_secret("google_oauth_client_id")
google_oauth_client_secret = config.get_secret("google_oauth_client_secret")
allowed_oauth_domain = config.get("allowed_oauth_domain")

# Enable required GCP APIs
artifact_registry_api = gcp.projects.Service(
    "artifact-registry-api",
    service="artifactregistry.googleapis.com",
    disable_on_destroy=False,
)

cloud_run_api = gcp.projects.Service(
    "cloud-run-api",
    service="run.googleapis.com",
    disable_on_destroy=False,
)

secretmanager_api = gcp.projects.Service(
    "secretmanager-api",
    service="secretmanager.googleapis.com",
    disable_on_destroy=False,
)

# Create a dedicated service account for Cloud Run
service_account = gcp.serviceaccount.Account(
    "recruitee-mcp-sa",
    account_id="recruitee-mcp-server",
    display_name="Recruitee MCP Server Service Account",
)

# Create secrets in GCP Secret Manager
recruitee_company_id_secret = gcp.secretmanager.Secret(
    "recruitee-company-id-secret",
    secret_id="recruitee_company_id",
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ),
    opts=pulumi.ResourceOptions(depends_on=[secretmanager_api]),
)

recruitee_company_id_version = gcp.secretmanager.SecretVersion(
    "recruitee-company-id-version",
    secret=recruitee_company_id_secret.id,
    secret_data=recruitee_company_id,
)

recruitee_api_token_secret = gcp.secretmanager.Secret(
    "recruitee-api-token-secret",
    secret_id="recruitee_api_token",
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ),
    opts=pulumi.ResourceOptions(depends_on=[secretmanager_api]),
)

recruitee_api_token_version = gcp.secretmanager.SecretVersion(
    "recruitee-api-token-version",
    secret=recruitee_api_token_secret.id,
    secret_data=recruitee_api_token,
)

# OAuth2 secrets (required for /mcp authentication)
oauth_secrets = []

if google_oauth_client_id:
    google_oauth_client_id_secret = gcp.secretmanager.Secret(
        "google-oauth-client-id-secret",
        secret_id="google_oauth_client_id",
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=pulumi.ResourceOptions(depends_on=[secretmanager_api]),
    )
    google_oauth_client_id_version = gcp.secretmanager.SecretVersion(
        "google-oauth-client-id-version",
        secret=google_oauth_client_id_secret.id,
        secret_data=google_oauth_client_id,
    )
    oauth_secrets.append(("google-oauth-client-id", google_oauth_client_id_secret))

if google_oauth_client_secret:
    google_oauth_client_secret_secret = gcp.secretmanager.Secret(
        "google-oauth-client-secret-secret",
        secret_id="google_oauth_client_secret",
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=pulumi.ResourceOptions(depends_on=[secretmanager_api]),
    )
    google_oauth_client_secret_version = gcp.secretmanager.SecretVersion(
        "google-oauth-client-secret-version",
        secret=google_oauth_client_secret_secret.id,
        secret_data=google_oauth_client_secret,
    )
    oauth_secrets.append(("google-oauth-client-secret", google_oauth_client_secret_secret))

# Grant service account access to secrets
all_secrets = [
    ("recruitee-company-id", recruitee_company_id_secret),
    ("recruitee-api-token", recruitee_api_token_secret),
] + oauth_secrets

for secret_name, secret in all_secrets:
    gcp.secretmanager.SecretIamMember(
        f"{secret_name}-access",
        secret_id=secret.id,
        role="roles/secretmanager.secretAccessor",
        member=service_account.email.apply(lambda email: f"serviceAccount:{email}"),
    )

# Create Artifact Registry repository for Docker images
artifact_repo = gcp.artifactregistry.Repository(
    "recruitee-mcp-repo",
    repository_id="recruitee-mcp-server",
    location=region,
    format="DOCKER",
    description="Docker repository for Recruitee MCP Server",
    opts=pulumi.ResourceOptions(depends_on=[artifact_registry_api]),
)

# Build and push Docker image to Artifact Registry
image_name = pulumi.Output.concat(
    region,
    "-docker.pkg.dev/",
    project_id,
    "/",
    artifact_repo.repository_id,
    "/recruitee-mcp-server:latest",
)

# Build Docker image
image = docker.Image(
    "recruitee-mcp-image",
    build=docker.DockerBuildArgs(
        context="../",
        dockerfile="../Dockerfile",
        platform="linux/amd64",
    ),
    image_name=image_name,
    registry=docker.RegistryArgs(
        server=pulumi.Output.concat(region, "-docker.pkg.dev"),
    ),
)

# Helper function to build OAuth environment variables
def _build_oauth_env_vars():
    """Build OAuth2 environment variables for Cloud Run (FastMCP OAuth Proxy)"""
    oauth_envs = []

    if google_oauth_client_id:
        oauth_envs.append(
            gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                name="GOOGLE_OAUTH_CLIENT_ID",
                value_source=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceArgs(
                    secret_key_ref=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceSecretKeyRefArgs(
                        secret="google_oauth_client_id",
                        version="latest",
                    )
                ),
            )
        )

    if google_oauth_client_secret:
        oauth_envs.append(
            gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                name="GOOGLE_OAUTH_CLIENT_SECRET",
                value_source=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceArgs(
                    secret_key_ref=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceSecretKeyRefArgs(
                        secret="google_oauth_client_secret",
                        version="latest",
                    )
                ),
            )
        )

    if allowed_oauth_domain:
        oauth_envs.append(
            gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                name="ALLOWED_OAUTH_DOMAIN",
                value=allowed_oauth_domain,
            )
        )

    return oauth_envs

# Create Cloud Run service
service = gcp.cloudrunv2.Service(
    "recruitee-mcp-service",
    name="recruitee-mcp-server",
    location=region,
    ingress="INGRESS_TRAFFIC_ALL",
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        service_account=service_account.email,
        containers=[
            gcp.cloudrunv2.ServiceTemplateContainerArgs(
                image=image.repo_digest,
                ports=[
                    gcp.cloudrunv2.ServiceTemplateContainerPortArgs(
                        container_port=8000,
                    )
                ],
                envs=[
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="RECRUITEE_COMPANY_ID",
                        value_source=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceArgs(
                            secret_key_ref=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceSecretKeyRefArgs(
                                secret="recruitee_company_id",
                                version="latest",
                            )
                        ),
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="RECRUITEE_API_TOKEN",
                        value_source=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceArgs(
                            secret_key_ref=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceSecretKeyRefArgs(
                                secret="recruitee_api_token",
                                version="latest",
                            )
                        ),
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="DOCUMENTS_DIR",
                        value=documents_dir,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="BASE_DEPLOY_URL",
                        # Use service URI for OAuth redirect URLs (FastMCP OAuth Proxy)
                        value=pulumi.Output.concat("https://recruitee-mcp-server-vfcymcigxa-nw.a.run.app"),
                    ),
                ] + _build_oauth_env_vars(),
                resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                    limits={
                        "cpu": "1",
                        "memory": "512Mi",
                    },
                ),
            )
        ],
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
            min_instance_count=1,
            max_instance_count=10,
        ),
    ),
    opts=pulumi.ResourceOptions(
        depends_on=[
            cloud_run_api,
            image,
            recruitee_company_id_version,
            recruitee_api_token_version,
        ]
    ),
)

# Make the service publicly accessible
iam_member = gcp.cloudrunv2.ServiceIamMember(
    "recruitee-mcp-invoker",
    name=service.name,
    location=region,
    role="roles/run.invoker",
    member="allUsers",
)

# Export the service URL
pulumi.export("service_url", service.uri)
pulumi.export("mcp_endpoint", pulumi.Output.concat(service.uri, "/mcp"))
pulumi.export("image_name", image.repo_digest)
