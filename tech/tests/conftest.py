# conftest.py - Coloque na raiz do projeto
import sys
import os
import pytest
import asyncio
from pytest_cov.embed import cleanup_on_sigterm
from unittest.mock import Mock, AsyncMock, patch

# Adiciona o diretório raiz ao sys.path para permitir importações relativas
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# Configuração para testes assíncronos
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Fixtures para uso em testes
@pytest.fixture
def mock_session():
    """Fixture for a mock database session."""
    session = Mock()
    return session


@pytest.fixture
def mock_order():
    """Fixture for a mock Order entity."""
    from tech.domain.entities.orders import Order, OrderStatus

    order = Order(
        id=1,
        total_price=100.0,
        product_ids="1,2,3",
        status=OrderStatus.RECEIVED
    )
    order.user_name = "Test User"
    order.user_email = "test@example.com"

    return order


@pytest.fixture
def mock_orders():
    """Fixture for a list of mock Order entities."""
    from tech.domain.entities.orders import Order, OrderStatus

    orders = [
        Order(
            id=1,
            total_price=100.0,
            product_ids="1,2,3",
            status=OrderStatus.RECEIVED
        ),
        Order(
            id=2,
            total_price=200.0,
            product_ids="4,5",
            status=OrderStatus.PREPARING
        ),
        Order(
            id=3,
            total_price=300.0,
            product_ids="6,7,8",
            status=OrderStatus.READY
        )
    ]

    # Add user info to first order
    orders[0].user_name = "User 1"
    orders[0].user_email = "user1@example.com"

    return orders


@pytest.fixture
def mock_order_repository():
    """Fixture for a mock OrderRepository."""
    mock_repo = Mock()

    # Configure o comportamento padrão do repositório aqui, se necessário
    mock_repo.get_by_id.return_value = None

    return mock_repo


@pytest.fixture
def mock_product_gateway():
    """Fixture for a mock ProductGateway."""
    mock_gateway = AsyncMock()

    # Configure o comportamento padrão do gateway aqui, se necessário
    mock_gateway.get_product.return_value = {"id": 1, "name": "Product 1", "price": 10.0}
    mock_gateway.get_products.return_value = [
        {"id": 1, "name": "Product 1", "price": 10.0},
        {"id": 2, "name": "Product 2", "price": 20.0}
    ]

    return mock_gateway


@pytest.fixture
def mock_user_gateway():
    """Fixture for a mock UserGateway."""
    mock_gateway = AsyncMock()

    # Configure o comportamento padrão do gateway aqui, se necessário
    mock_gateway.get_user_by_cpf.return_value = {
        "id": 1,
        "username": "Test User",
        "email": "test@example.com",
        "cpf": "12345678901"
    }

    return mock_gateway

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Limpar ao receber sinal de término
cleanup_on_sigterm()

# Configurações para os testes
def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


# Adiciona o diretório raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Define o ambiente como teste
os.environ["ENVIRONMENT"] = "test"

# Configura SQLite para não verificar threads (evita erros de threading)
os.environ["DATABASE_URL"] = "sqlite:///./test.db?check_same_thread=False"


# Mock para a sessão de banco de dados
@pytest.fixture
def mock_db_session():
    """Mock para a sessão de banco de dados SQLAlchemy."""
    with patch('tech.infra.databases.database.get_session') as mock_session:
        session_instance = Mock()
        mock_session.return_value = session_instance

        # Configurar métodos comuns da sessão
        session_instance.commit.return_value = None
        session_instance.rollback.return_value = None
        session_instance.close.return_value = None
        session_instance.query.return_value = session_instance
        session_instance.filter.return_value = session_instance
        session_instance.all.return_value = []
        session_instance.first.return_value = None

        yield session_instance


# Mock para o repositório de pedidos
@pytest.fixture
def mock_order_repository():
    """Mock para o repositório de pedidos."""
    with patch('tech.infra.repositories.sql_alchemy_order_repository.SQLAlchemyOrderRepository') as mock_repo:
        repo_instance = Mock()
        mock_repo.return_value = repo_instance

        # Configurar métodos do repositório
        repo_instance.get_by_id.return_value = None
        repo_instance.list_orders.return_value = []
        repo_instance.add.return_value = None
        repo_instance.update.return_value = None
        repo_instance.delete.return_value = None

        yield repo_instance


# Plugin para suportar testes assíncronos
def pytest_configure(config):
    """Configuração do pytest."""
    pytest.skip_if_no_async = lambda msg=None: pytest.skip(msg or "requires async support")
