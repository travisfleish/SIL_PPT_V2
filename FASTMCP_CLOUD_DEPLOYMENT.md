# 🚀 FastMCP Cloud Deployment Guide

Deploy your Sports Innovation Lab MCP server to FastMCP Cloud for remote access and easy integration with Claude.

## 🎯 **Why FastMCP Cloud?**

- **Remote Access**: Access your MCP server from anywhere
- **Production Ready**: Built-in scaling, monitoring, and reliability
- **Easy Integration**: Perfect for Claude's "Remote MCP server URL" field
- **Free Tier**: Available to get started
- **Managed Infrastructure**: No server maintenance required

## 📋 **Prerequisites**

1. **FastMCP CLI installed**
2. **FastMCP Cloud account** (sign up at [fastmcp.cloud](https://www.fastmcp.cloud/))
3. **Your MCP server working locally**

## 🔧 **Step 1: Install FastMCP CLI**

```bash
pip install fastmcp
```

## 🔐 **Step 2: Authenticate with FastMCP Cloud**

```bash
fastmcp auth
```

Follow the prompts to sign in to your FastMCP Cloud account.

## 📁 **Step 3: Prepare Your Project**

Your project is already prepared with:
- ✅ `mcp_server_cloud.py` - Cloud-ready MCP server
- ✅ `fastmcp.yaml` - Deployment configuration
- ✅ All required dependencies

## 🚀 **Step 4: Deploy to FastMCP Cloud**

```bash
# Deploy your MCP server
fastmcp deploy

# Or specify the config file explicitly
fastmcp deploy --config fastmcp.yaml
```

## 📊 **Step 5: Monitor Deployment**

```bash
# Check deployment status
fastmcp status

# View logs
fastmcp logs

# List all deployments
fastmcp list
```

## 🌐 **Step 6: Get Your Remote URL**

After successful deployment, you'll get a URL like:
```
https://your-server-name.fastmcp.cloud
```

## 🔗 **Step 7: Connect to Claude**

1. **Open Claude Desktop**
2. **Go to Settings → Connectors**
3. **Click "Add custom connector"**
4. **Fill in:**
   - **Name**: Sports Innovation Lab
   - **Remote MCP server URL**: `https://your-server-name.fastmcp.cloud`
5. **Click "Add"**

## 🧪 **Step 8: Test the Connection**

Once connected, test your MCP server by asking Claude to:
- "List all available sports teams"
- "Get the configuration for the Utah Jazz"
- "Show me the system status"

## 📈 **Step 9: Monitor and Scale**

```bash
# Check server health
fastmcp health

# View metrics
fastmcp metrics

# Scale up/down
fastmcp scale --instances 3
```

## 🔄 **Updating Your Server**

```bash
# Deploy updates
fastmcp deploy

# Or force redeploy
fastmcp deploy --force
```

## 🛠️ **Troubleshooting**

### **Common Issues:**

1. **Authentication Failed**
   ```bash
   fastmcp auth --force
   ```

2. **Deployment Failed**
   ```bash
   fastmcp logs --tail 100
   ```

3. **Environment Variables Missing**
   - Check your `.env` file
   - Ensure all required variables are set

4. **Dependencies Issues**
   ```bash
   fastmcp deploy --rebuild
   ```

### **Debug Mode:**

```bash
# Enable debug logging
fastmcp deploy --debug

# Check server configuration
fastmcp config
```

## 📊 **Performance Monitoring**

FastMCP Cloud provides:
- **Real-time metrics**: Response times, error rates
- **Automatic scaling**: Based on CPU utilization
- **Health checks**: Automatic failure detection
- **Log aggregation**: Centralized logging

## 💰 **Pricing**

- **Free Tier**: Available for development and testing
- **Paid Plans**: Scale based on usage and performance needs
- **Pay-as-you-go**: Only pay for what you use

## 🎉 **Success!**

Once deployed, your Sports Innovation Lab MCP server will be:
- ✅ **Accessible remotely** from anywhere
- ✅ **Integrated with Claude** via the Remote MCP server URL
- ✅ **Production ready** with monitoring and scaling
- ✅ **Easy to maintain** with automatic updates

## 🔗 **Next Steps**

1. **Deploy**: `fastmcp deploy`
2. **Connect**: Add the remote URL to Claude
3. **Test**: Verify all tools and resources work
4. **Scale**: Monitor performance and adjust as needed

## 📚 **Additional Resources**

- [FastMCP Cloud Documentation](https://www.fastmcp.cloud/)
- [FastMCP CLI Reference](https://docs.fastmcp.cloud/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

---

**Ready to deploy?** Run `fastmcp deploy` and get your remote MCP server URL! 🚀
