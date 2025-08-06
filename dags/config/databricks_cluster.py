from dags.utils.terraform_outputs import TerraformOutputManager

def build_job_cluster_spec(datalake_name, spn_client_id, tenant_id, secret_scope, secret_key):
    return [
        {
            "job_cluster_key": "cluster-data-analytics",
            "new_cluster": {
                "spark_version": "13.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2",
                "num_workers": 1,
                "spark_conf": {
                    f"fs.azure.account.auth.type.{datalake_name}.dfs.core.windows.net": "OAuth",
                    f"fs.azure.account.oauth.provider.type.{datalake_name}.dfs.core.windows.net": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
                    f"fs.azure.account.oauth2.client.id.{datalake_name}.dfs.core.windows.net": spn_client_id,
                    f"fs.azure.account.oauth2.client.secret.{datalake_name}.dfs.core.windows.net": f"{{{{secrets/{secret_scope}/{secret_key}}}}}",
                    f"fs.azure.account.oauth2.client.endpoint.{datalake_name}.dfs.core.windows.net": f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
                },
                "data_security_mode": "USER_ISOLATION",
                "custom_tags": {
                    "Environment": "analytics",
                    "User": "Duque",
                    "Project": "Datamaster"
                },
                "cluster_source": "JOB",
                "policy_id": TerraformOutputManager().get_output('cluster_policy')
            }
        }
    ]