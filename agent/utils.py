import asyncio
import socket

# async def getLocalIP():
#     try:
#         # Асинхронное создание TCP-соединения для определения локального IP
#         reader, writer = await asyncio.open_connection('8.8.8.8', 80)
#         local_ip = writer.get_extra_info('sockname')[0]
#         writer.close()
#         await writer.wait_closed()
#         return local_ip
#     except Exception:
#         try:
#             # Асинхронное разрешение DNS через цикл событий
#             loop = asyncio.get_running_loop()
#             hostname = await loop.run_in_executor(None, socket.gethostname)
#             local_ip = await loop.run_in_executor(None, socket.gethostbyname, hostname)
#             return local_ip
#         except Exception:
#             return "127.0.0.1"