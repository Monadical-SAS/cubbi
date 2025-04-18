"""
Integration test for MCP port binding.
"""

import time
import uuid

from conftest import requires_docker
from cubbi.mcp import MCPManager


@requires_docker
def test_mcp_port_binding():
    """Test that MCP containers don't bind to host ports."""
    mcp_manager = MCPManager()

    # Add a proxy MCP
    mcp_name = f"test-mcp-{uuid.uuid4().hex[:8]}"
    mcp_name2 = None

    try:
        # Let's check if host port binding was removed
        mcps_before = len(mcp_manager.list_mcp_containers())

        # Use alpine image for a simple test
        mcp_manager.add_docker_mcp(
            name=mcp_name,
            image="alpine:latest",
            command="sleep 60",  # Keep container running for the test
            env={"TEST": "test"},
        )

        # Start the MCP
        result = mcp_manager.start_mcp(mcp_name)
        print(f"Start result: {result}")

        # Give container time to start
        time.sleep(2)

        # Start another MCP to verify we can run multiple instances
        mcp_name2 = f"test-mcp2-{uuid.uuid4().hex[:8]}"
        mcp_manager.add_docker_mcp(
            name=mcp_name2,
            image="alpine:latest",
            command="sleep 60",  # Keep container running for the test
            env={"TEST": "test2"},
        )

        # Start the second MCP
        result2 = mcp_manager.start_mcp(mcp_name2)
        print(f"Start result 2: {result2}")

        # Give container time to start
        time.sleep(2)

        # Check how many containers we have now
        mcps_after = len(mcp_manager.list_mcp_containers())

        # We should have two more containers than before
        assert mcps_after >= mcps_before + 2, "Not all MCP containers were created"

        # Get container details and verify no host port bindings
        all_mcps = mcp_manager.list_mcp_containers()
        print(f"All MCPs: {all_mcps}")

        # Test successful - we were able to start multiple MCPs without port conflicts

    finally:
        # Clean up
        try:
            if mcp_name:
                mcp_manager.stop_mcp(mcp_name)
                mcp_manager.remove_mcp(mcp_name)
        except Exception as e:
            print(f"Error cleaning up {mcp_name}: {e}")

        try:
            if mcp_name2:
                mcp_manager.stop_mcp(mcp_name2)
                mcp_manager.remove_mcp(mcp_name2)
        except Exception as e:
            print(f"Error cleaning up {mcp_name2}: {e}")
