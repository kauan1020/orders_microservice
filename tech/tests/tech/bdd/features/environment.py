# tests/bdd/environment.py (versão simplificada)
import os
from unittest.mock import patch, MagicMock, AsyncMock


def before_all(context):
    """Configuração global antes de todos os cenários."""
    # Configurar variáveis de ambiente para testes
    os.environ["SERVICE_PRODUCTS_URL"] = "http://test-product-service"
    os.environ["SERVICE_USERS_URL"] = "http://test-user-service"
    os.environ["PRODUCT_GATEWAY_RESILIENCE"] = "none"  # Desativar circuit breaker para testes
    os.environ["USER_GATEWAY_RESILIENCE"] = "none"  # Desativar circuit breaker para testes

    # Usar banco de dados em memória para testes
    os.environ["DATABASE_URL"] = "sqlite:///:memory:?check_same_thread=False"

    # Lista para rastrear patches ativos
    context.active_patches = []

    # Patch global para database session
    db_session_patch = patch('tech.infra.databases.database.get_session')
    mock_session = db_session_patch.start()

    # Mock da sessão do banco
    mock_session_instance = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_session_instance
    mock_session.return_value.__aexit__.return_value = None

    # Patch para o SQLAlchemy session
    context.session_patch = patch('sqlalchemy.orm.Session')
    context.mock_session_class = context.session_patch.start()
    context.mock_session_instance = MagicMock()
    context.mock_session_class.return_value = context.mock_session_instance

    # Patch para o repositório
    context.repo_patch = patch('tech.infra.repositories.sql_alchemy_order_repository.SQLAlchemyOrderRepository')
    context.mock_repo_class = context.repo_patch.start()
    context.mock_repo_instance = MagicMock()
    context.mock_repo_class.return_value = context.mock_repo_instance

    # Adicionar à lista de patches ativos
    context.active_patches.extend([db_session_patch, context.session_patch, context.repo_patch])


def after_all(context):
    """Limpeza após todos os cenários."""
    # Remover variáveis de ambiente
    for env_var in ["SERVICE_PRODUCTS_URL", "SERVICE_USERS_URL",
                    "PRODUCT_GATEWAY_RESILIENCE", "USER_GATEWAY_RESILIENCE",
                    "DATABASE_URL"]:
        if env_var in os.environ:
            del os.environ[env_var]

    # Parar todos os patches ativos
    for p in context.active_patches:
        try:
            p.stop()
        except Exception as e:
            print(f"Erro ao parar patch: {str(e)}")


def before_scenario(context, scenario):
    """Configuração antes de cada cenário."""
    # Reset patches específicos do cenário
    context.scenario_patches = []

    # Reiniciar mocks para cada cenário
    context.mock_session_instance.query.return_value.filter.return_value.first.return_value = None
    context.mock_session_instance.query.return_value.filter.return_value.all.return_value = []
    context.mock_session_instance.commit.return_value = None

    # Reiniciar mock do repositório
    context.mock_repo_instance.get_by_id.return_value = None
    context.mock_repo_instance.list_orders.return_value = []
    context.mock_repo_instance.add.return_value = None
    context.mock_repo_instance.update.return_value = None
    context.mock_repo_instance.delete.return_value = None


def after_scenario(context, scenario):
    """Limpeza após cada cenário."""
    # Parar patches específicos do cenário
    for p in getattr(context, 'scenario_patches', []):
        try:
            p.stop()
        except Exception as e:
            print(f"Erro ao parar patch de cenário: {str(e)}")