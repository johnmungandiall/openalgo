# Pi42 Test API Credentials

**IMPORTANT**: These are test credentials for development only. Never commit this file to version control.

## API Configuration

**Label**: openalgointigration

**API Key**: `013cbaef14f0ed7715d49e9bbc6fad3e`

**Secret Key**: `e97023f6cf99effe53c18d9891c5ab69`

## API Restrictions

- **Read**: ✅ Enabled
- **Trade Futures**: ✅ Enabled

## Usage in Development

Add these credentials to your `.env` file:

```bash
# Pi42 Test Credentials
PI42_API_KEY=013cbaef14f0ed7715d49e9bbc6fad3e
PI42_API_SECRET=e97023f6cf99effe53c18d9891c5ab69
```

## Testing Endpoints

Use these credentials to test:
- Market data fetching
- Order placement (futures)
- Position management
- Account information
- Funding rates
- Leverage settings

## Security Notes

1. **Never commit** this file to git
2. **Never share** these credentials publicly
3. **Rotate keys** after testing is complete
4. **Use separate keys** for production
5. **Monitor API usage** during testing

## API Documentation

- **Base URL**: `https://api.pi42.com`
- **Docs**: https://docs.pi42.com/
- **Rate Limits**: Check documentation for current limits

## Test Checklist

- [ ] Authentication working (signature generation)
- [ ] Market data retrieval
- [ ] Order placement (MARKET, LIMIT)
- [ ] STOP orders (STOP_MARKET, STOP_LIMIT)
- [ ] Position management
- [ ] Leverage adjustment
- [ ] Margin operations
- [ ] Funding rate queries
- [ ] WebSocket connection
- [ ] Error handling

---

**Created**: 2026-04-18
**Purpose**: Development and testing of Pi42 integration
**Status**: Active test credentials
