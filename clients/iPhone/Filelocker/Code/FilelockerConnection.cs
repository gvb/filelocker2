using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Net;
using System.Xml;
using System.Text;
using System.Text.RegularExpressions;
using System.Reflection;

namespace Filelocker
{
	public class FilelockerConnection
	{
		private CookieContainer FLCOOKIE;
		public Dictionary<string, float>FILE_DOWNLOADS;
		public string USERID;
		private string FL_SERVER;
		private string CLI_KEY;
		public bool connected;
		public List<Group> USER_GROUPS;
		

		//This stuff makes the class a singleton
		private static FilelockerConnection instance;
		private FilelockerConnection() 
		{
			FLCOOKIE = new CookieContainer();
			USER_GROUPS = new List<Group>();
			FILE_DOWNLOADS = new Dictionary<string, float>();
			connected = false;
		}
		public static FilelockerConnection Instance
		{
			get
			{
				if (instance == null)
				{
					instance = new FilelockerConnection();
				}
				return instance;
			}
		}
		// End singleton code
		
		public bool login(string server, string username, string clikey)
		{
			FL_SERVER = server;
			CLI_KEY = clikey;
			USERID = username;
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("userId", username);
            postParameters.Add("CLIkey", CLI_KEY);
            Dictionary<string, string> response = this.postDataToServer(server + "/cli_interface/CLI_login", postParameters, false);
			if (response["fMessages"].Equals(""))
			{
				connected = true;
				return true;
			}
			else
			{
				throw new FilelockerException("Unable to log in: "+response["fMessages"]);
			}
		}
		
		// returns the CLI Key if everything works as expected
		public string registerWithServer(string server, string username, string password)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("username", username);
            postParameters.Add("password", password);
            postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(server + "/cli_interface/register_client", postParameters, false);
				if (response["fMessages"].Equals(""))
					return response["data"].Trim();
				else
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
            
		}	
		
		public void deleteFile(string fileId)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("fileIds", fileId);
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/file_interface/delete_files", postParameters, false);
				if (!response["fMessages"].Equals(""))
					throw new FilelockerException(response["fMessages"]);					
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		
		public void toggleFileNotifications(string fileId, bool notify)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("fileId", fileId);
			postParameters.Add("notifyOnDownload", notify.ToString().ToLower());
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/file_interface/update_file", postParameters, false);
				if (!response["fMessages"].Equals(""))
					throw new FilelockerException(response["fMessages"]);					
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		
		public void shareFilesWithGroup(List<string> fileIds, string groupId)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			string fileIdCSV = string.Join(",", fileIds);
            postParameters.Add("fileIds", fileIdCSV);
			postParameters.Add("groupId", groupId);
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/share_interface/create_private_share", postParameters, false);
				if (!response["fMessages"].Equals(""))
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		public User shareFilesWithUser(List<string> fileIds, string userId)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			string fileIdCSV = string.Join(",", fileIds);
            postParameters.Add("fileIds", fileIdCSV);
			postParameters.Add("targetId", userId);
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/share_interface/create_private_share", postParameters, false);
				if (!response["fMessages"].Equals(""))
					throw new FilelockerException(response["fMessages"]);
				else
				{
					User shareUser = new User();
					XmlDocument doc = new XmlDocument();
					string userXML = response["data"];
					doc.LoadXml(userXML);
		            foreach (XmlNode user in doc.ChildNodes)
		            {
						Dictionary<string, string> userDictionary = new Dictionary<string, string>();
						foreach (XmlNode userAttribute in user)
						{
							userDictionary[userAttribute.Name] = userAttribute.InnerText;
						}
						shareUser = CreateObjectFromValues<User>(userDictionary);	
					}
					return shareUser;
				}
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		public void unshareFilesWithUser(List<string> fileIds, string userId)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			string fileIdCSV = string.Join(",", fileIds);
            postParameters.Add("fileIds", fileIdCSV);
			postParameters.Add("targetId", userId);
			postParameters.Add("shareType", "private");
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/share_interface/delete_share", postParameters, false);
				if (!response["fMessages"].Equals(""))
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		public void unshareFilesWithGroup(List<string> fileIds, string groupId)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			string fileIdCSV = string.Join(",", fileIds);
            postParameters.Add("fileIds", fileIdCSV);
			postParameters.Add("targetId", groupId);
			postParameters.Add("shareType", "private_group");
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/share_interface/delete_share", postParameters, false);
				if (!response["fMessages"].Equals(""))
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		public bool hideShare(string fileId)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("fileIds", fileId);
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/file_interface/hide_share", postParameters, false);
				if (response["fMessages"].Equals(""))
					return true;
				else
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		
		public void sendMessage(List<string> recipientIds, string subject, string body)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			string recipientIdCSV = string.Join(",", recipientIds);
            postParameters.Add("recipientIds", recipientIdCSV.ToString());
			postParameters.Add("subject", subject);
			postParameters.Add("body", body);
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/message_interface/send_message", postParameters, false);
				if (!response["fMessages"].Equals(""))
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		
		public bool deleteMessages(List<string> messageIds)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			StringBuilder messageIdCSV = new StringBuilder("");
			foreach (string messageId in messageIds)
			{
				messageIdCSV.Append(messageId);
				messageIdCSV.Append(",");
			}
            postParameters.Add("messageIds", messageIdCSV.ToString());
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/message_interface/delete_messages", postParameters, false);
				if (response["fMessages"].Equals(""))
					return true;
				else
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
		public bool markMessageAsRead(string messageId)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("messageId", messageId);
			postParameters.Add("format", "cli");
			try
			{
				Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/message_interface/read_message", postParameters, false);
				if (response["fMessages"].Equals(""))
					return true;
				else
					throw new FilelockerException(response["fMessages"]);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
		}
			
		public Dictionary<string, List<FLMessage>> getAllMessages()
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			Dictionary<string, List<FLMessage>> flMessages = new Dictionary<string, List<FLMessage>>();
			postParameters.Add("format", "cli");
			Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/message_interface/get_messages", postParameters, false);
			
			try
			{
				XmlDocument doc = new XmlDocument();
				string messageListXML = response["data"];
				doc.LoadXml(messageListXML);
	            foreach (XmlNode messages in doc.ChildNodes)
	            {
					//2 boxes, inbox and outbox
					foreach (XmlNode messageBox in messages.ChildNodes)
					{
						string sectionName = "";
						if (messageBox.Attributes != null)
						{
							foreach (XmlAttribute attr in messageBox.Attributes)
							{
								if (attr.Name == "title")
									sectionName = attr.Value;
								
							}
						}
						else
						{
							throw new FilelockerException("The XML received from the server was poorly formatted.");
						}
						
						flMessages[sectionName] = new List<FLMessage>();
						foreach (XmlNode message in messageBox.ChildNodes)
						{
							Dictionary<string, string> messageDictionary = new Dictionary<string, string>();
							foreach (XmlNode node in message.ChildNodes)
							{
								messageDictionary[node.Name] = node.InnerText;
							}
							FLMessage newMessage = CreateObjectFromValues<FLMessage> (messageDictionary);
							flMessages[sectionName].Add(newMessage);
						}
					}
	            }	
				return flMessages;
			}
			catch(FilelockerException fe)
			{
				throw fe;
			}
			catch (System.Xml.XmlException xmle)
			{
				Console.WriteLine("Problem with the XML from the server: {0}", xmle.Message);
				throw new FilelockerException("XML from server was poorly formatted");
			}
			catch (Exception e)
			{
				Console.Write("Problem populating message list: {0}", e.Message);
				throw new FilelockerException("Couldn't get message list");
			}
		}
		
		public List<KeyValuePair<string, List<FLFile>>> populatFileList(List<string> downloadedFileIds)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
			postParameters.Add("format", "cli");
			Dictionary<string, string> response = this.postDataToServer(FL_SERVER + "/files", postParameters, false);
			List<KeyValuePair<string, List<FLFile>>> fileSectionKVPList = new List<KeyValuePair<string, List<FLFile>>>();
			XmlDocument doc = new XmlDocument();
			string fileListXML = "";
			try
			{
				fileListXML += response["data"];
				doc.LoadXml(fileListXML);
				//FLFile(int fileId, string fileName, string fileOwnerId, long fileSizeBytes, string fileType, string fileNotes, DateTime fileUploadedDatetime, DateTime fileExpirationDatetime, bool filePasswdAvScan, string fileStatus, bool fileNotifyOnDownload)
	            XmlNode filesAndGroups = doc.ChildNodes[0];
				XmlNode fileList = filesAndGroups.ChildNodes[0];
				foreach (XmlNode sectionNode in fileList.ChildNodes)
				{
					KeyValuePair<string, List<FLFile>> sectionFilesKvp = new KeyValuePair<string, List<FLFile>>();
					string sectionName = "";
					if (sectionNode.Attributes != null)
					{
						foreach (XmlAttribute attr in sectionNode.Attributes)
						{
							sectionName = attr.Value;
						}
					}
					else
					{
						throw new FilelockerException("The XML received from the server was poorly formatted.");
					}
					List<FLFile> filesList = new List<FLFile>();
					List<User> userList = new List<User>();
					foreach (XmlNode flFile in sectionNode.ChildNodes)
					{
						Dictionary<string, string> fileDictionary = new Dictionary<string, string>();
						foreach (XmlNode node in flFile.ChildNodes)
						{
							if (node.Name == "fileShares") //Parse through users who this file has been shared with
							{
								foreach (XmlNode shareUserNode in node)
								{
									Dictionary<string, string> userDictionary = new Dictionary<string, string>();
									foreach(XmlNode userInfo in shareUserNode)
									{
										userDictionary[userInfo.Name] = userInfo.InnerText;
									}
									User shareUser = CreateObjectFromValues<User>(userDictionary);
									userList.Add(shareUser);
								}
							}
							else
								fileDictionary[node.Name] = node.InnerText;
						}
						FLFile newFile = CreateObjectFromValues<FLFile>(fileDictionary);
						newFile.shareUsers = userList;
						newFile.downloaded =  downloadedFileIds.Contains(newFile.fileId) ? true : false;
						filesList.Add(newFile);
					}
					sectionFilesKvp = new KeyValuePair<string, List<FLFile>>(sectionName, filesList);
					fileSectionKVPList.Add(sectionFilesKvp);
				}
				XmlNode groupList = filesAndGroups.ChildNodes[1];
				USER_GROUPS = new List<Group>();
				foreach (XmlNode groupNode in groupList)
				{
					string groupName = groupNode.Attributes["name"].Value;
					string groupId = groupNode.Attributes["id"].Value;
					Group newGroup = new Group(groupName, groupId);
					Dictionary<string, string> userDictionary = new Dictionary<string, string>();
					List<User> members = new List<User>();
					XmlNode membersNode = groupNode.ChildNodes[0];
					foreach (XmlNode memberNode in membersNode)
					{
						userDictionary[memberNode.Name] = memberNode.InnerText;
						User newUser = CreateObjectFromValues<User>(userDictionary);

						members.Add(newUser);
					}
					XmlNode fileIdsNode = groupNode.ChildNodes[1];
					List<string> fileIdsSharedWithGroup = new List<string>();
					foreach (XmlNode fileIdNode in fileIdsNode)
					{
						fileIdsSharedWithGroup.Add(fileIdNode.InnerText);
					}
					newGroup.groupMembers = members;
					newGroup.filesSharedWithGroup = fileIdsSharedWithGroup;
					USER_GROUPS.Add(newGroup);
				}
				return fileSectionKVPList;
			}
			catch(FilelockerException fe)
			{
				throw fe;
			}
			catch (Exception e)
			{
				Console.Write("Problem populating file list: {0}", e.Message);
				throw new FilelockerException("Couldn't get file list"+e.Message);
			}
		}
		
        public T CreateObjectFromValues<T>(Dictionary<string, string> values) where T : new()
        {
            T targetObject= new T();
		
            Dictionary<string, PropertyInfo> propertyLookup = new Dictionary<string, PropertyInfo>(); 
         	foreach (PropertyInfo propertyInfo in typeof(T).GetProperties())
            {
				if (!propertyLookup.ContainsKey(propertyInfo.Name.ToLower()))
                {
                    propertyLookup.Add(propertyInfo.Name.ToLower(), propertyInfo);
                }
            }
			foreach (string columnName in values.Keys)
            {
                if (propertyLookup.ContainsKey(columnName.ToLower()))
                {
                    if (propertyLookup[columnName.ToLower()].PropertyType == typeof(DateTime))
					{
						DateTime t;
						DateTime.TryParse(values[columnName], out t);
						propertyLookup[columnName.ToLower()].SetValue(targetObject, t, null);	
					}
					else if (propertyLookup[columnName.ToLower()].PropertyType == typeof(bool))
					{
						bool tf;
						bool.TryParse(values[columnName], out tf);
						propertyLookup[columnName.ToLower()].SetValue(targetObject, tf, null);

					}
					else if (propertyLookup[columnName.ToLower()].PropertyType == typeof(long))
					{
						long l;
						long.TryParse(values[columnName], out l);
						propertyLookup[columnName.ToLower()].SetValue(targetObject, l, null);
					}
					else{
						propertyLookup[columnName.ToLower()].SetValue(targetObject, values[columnName], null);
					}
                }
            }
            return targetObject;
        }
		
        public Dictionary<string, string> postDataToServer(string server, Dictionary<string, string> postParameters, bool fileDownload) 
        {
			
			string responseText = "";
            // Determine proper handler and get the response.
			StreamReader reader = null;
			Stream responseStream = null;
			Stream localStream = null;
			WebResponse response = null;
			HttpWebRequest request = null;
			
			try
			{
				//convert post parameters into URLencoded post data
	            string postData = "";
	            foreach (string key in postParameters.Keys)
	            {
	                postData += key + "=" + postParameters[key] + "&";
	            }
	            request = (HttpWebRequest)WebRequest.Create(server);
				request.CookieContainer = FLCOOKIE;
				
	            // Set the Method property of the request to POST.
	            request.Method = "POST";
				request.Timeout = 5000;
	            // Create POST data and convert it to a byte array.
	            byte[] byteArray = Encoding.UTF8.GetBytes(postData);
	            // Set the ContentType property of the WebRequest.
	            request.ContentType = "application/x-www-form-urlencoded";
	            // Set the ContentLength property of the WebRequest.
	            request.ContentLength = byteArray.Length;
	            // Get the request stream.
	            using (Stream dataStream = request.GetRequestStream())
	            {
	                dataStream.Write(byteArray, 0, byteArray.Length);
	            }
	            using (response = request.GetResponse())
	            {			
					
					HttpStatusCode statusCode = ((HttpWebResponse)response).StatusCode;
					if (true) //Check https status code TODO
					{
						foreach (Cookie cookie in ((HttpWebResponse)response).Cookies)
						{
							FLCOOKIE.Add(cookie);
						}
		                // Get the stream containing content returned by the server.
		                using (responseStream = response.GetResponseStream())
		                {
		                    if (!fileDownload)
							{
								using (reader = new StreamReader(responseStream))
		                    	{
									string responseFromServer = reader.ReadToEnd();
			                        // Display the content.
		                        	responseText = responseFromServer;
								}
								return parseFilelockerResponse(responseText);
								
							}
							else
							{
								long fileSizeBytes = response.ContentLength;
								var documents = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
								long bytesProcessed = 0;
								string fileId = postParameters["fileId"];
								FILE_DOWNLOADS[fileId] = 0f;
								string fileExtension = "";
								for (int i=0;i<response.Headers.Count;++i)
								{
									string key = response.Headers.Keys[i];
									string hValue = response.Headers[i];
									if (key.Equals("Content-Disposition"))
								    {
										Regex filenameRegex = new Regex("filename=\"?(?<filename>[^;\"]+)[;\"/s]");
										Match m = filenameRegex.Match(hValue);
										if (m.Success)
										{
											fileExtension = System.IO.Path.GetExtension(m.Groups["filename"].Value);
										}
									}
								}
								string filename = string.Format("{0}{1}", fileId, fileExtension);
								
								// Create the local file
								localStream = File.Create(Path.Combine(documents, filename));
								
								// Allocate a 1k buffer
								byte[] buffer = new byte[1024];
								int bytesRead;
								
								// Simple do/while loop to read from stream until
								// no bytes are returned
							    do
							    {
									// Read data (up to 1k) from the stream
									bytesRead = responseStream.Read(buffer, 0, buffer.Length);
									
									// Write the data to the local file
									localStream.Write(buffer, 0, bytesRead);
									
									// Increment total bytes processed
									bytesProcessed += bytesRead;
									FILE_DOWNLOADS[fileId] = (((float)bytesProcessed/(float)fileSizeBytes));
							    } 
								while (bytesRead > 0);
								FILE_DOWNLOADS[fileId] = 1f;
								responseText = "Downloaded";
								return new Dictionary<string, string>(){{"sMessages",responseText},{"fMessages",""}};
							}
		                }
					}
					else
					{
						Console.Write("Status description was not ok: {0}", statusCode.ToString());
						throw new FilelockerException("Communication response status error");
					}
	            }
			}
			catch (Exception e)
			{
				Console.WriteLine("Problem talking to Filelocker server: {0}", e.Message);
				throw new FilelockerException("Communication error: "+ e.Message);
			}
			finally
			{
				if (response != null) response.Close();
				if (reader != null) reader.Close();
				if (localStream != null) localStream.Close();
				if (responseStream != null) responseStream.Close();
			}
        }
		
		public Dictionary<string, string> HttpUploadFile(string url, byte[] mediaBytes, string fileName, Dictionary<string, string> postParameters) 
		{
	        string boundary = "---------------------------" + DateTime.Now.Ticks.ToString("x");
	        byte[] boundarybytes = System.Text.Encoding.ASCII.GetBytes("\r\n--" + boundary + "\r\n");
			string contentType = "application/octet-stream";
			string response="";
	        HttpWebRequest wr = (HttpWebRequest)WebRequest.Create(url);
	        wr.ContentType = "application/octet-stream";// + boundary;
	        wr.Method = "POST";
			wr.Headers.Set("x-file-name", fileName);
	        wr.KeepAlive = true;
			wr.CookieContainer = FLCOOKIE;
			MemoryStream fileDataStream = new MemoryStream(mediaBytes);
	        Stream rs = wr.GetRequestStream();
	
//	        string formdataTemplate = "Content-Disposition: form-data; name=\"{0}\"\r\n\r\n{1}";
//	        foreach (string key in postParameters.Keys)
//	        {
//	            rs.Write(boundarybytes, 0, boundarybytes.Length);
//	            string formitem = string.Format(formdataTemplate, key, postParameters[key]);
//	            byte[] formitembytes = System.Text.Encoding.UTF8.GetBytes(formitem);
//	            rs.Write(formitembytes, 0, formitembytes.Length);
//	        }
	        //rs.Write(boundarybytes, 0, boundarybytes.Length);
	        //string headerTemplate = "Content-Disposition: form-data; name=\"{0}\"; fileName=\"{1}\"\r\nContent-Type: {2}\r\n\r\n";
	        //string header = string.Format(headerTemplate, "uploadForm", fileName, contentType);
	        //byte[] headerbytes = System.Text.Encoding.UTF8.GetBytes(header);
	        //rs.Write(headerbytes, 0, headerbytes.Length);

	
	        byte[] buffer = new byte[4096];
	        int bytesRead = 0;
	        while ((bytesRead = fileDataStream.Read(buffer, 0, buffer.Length)) != 0) 
			{
				rs.Write(buffer, 0, bytesRead);
	        }
	        fileDataStream.Close();
	
	        byte[] trailer = System.Text.Encoding.ASCII.GetBytes("\r\n--" + boundary + "--\r\n");
	        //rs.Write(trailer, 0, trailer.Length);
	        rs.Close();
	
	        WebResponse wresp = null;
			
	        try 
			{
	            wresp = wr.GetResponse();
	            Stream stream2 = wresp.GetResponseStream();
	            StreamReader reader2 = new StreamReader(stream2);
				response = reader2.ReadToEnd();
	        } 
			catch (Exception e) 
			{
	            Console.WriteLine("Error uploading file: {0}", e.Message);
	            if (wresp != null) 
				{
	                wresp.Close();
	                wresp = null;
	            }
	        } 
			finally 
			{
	            wr = null;
	        }
			return parseFilelockerResponse(response);
        }
		
		public Dictionary<string, string> parseFilelockerResponse(string response)
        {
			Dictionary<string, string> formattedResponse = new Dictionary<string, string>();
            string sMessages = "";
            string fMessages = "";
            string data = "";
            if (!response.StartsWith("Error:"))
            {
                XmlDocument doc = new XmlDocument();
                doc.LoadXml(response);
                foreach (XmlElement item in doc.GetElementsByTagName("info"))
                {
                    sMessages += item.InnerText + ". ";
                }
                foreach (XmlElement item in doc.GetElementsByTagName("error"))
                {
                    fMessages += item.InnerText + ". ";
                }
				try
				{
					XmlNode dataNode = doc.GetElementsByTagName("data")[0];
					data = dataNode.InnerXml;
				}
				catch (Exception e)
				{
					data = "";
					Console.Write("Problem getting data node: {0}", e.Message);
				}

            }
            else 
            {
                fMessages += response + ". "; //This means that the response is already some kind of error message, not an XML response
            }
            formattedResponse.Add("sMessages", sMessages);
            formattedResponse.Add("fMessages", fMessages);
            formattedResponse.Add("data", data);
            return formattedResponse;
        }
		
		public bool downloadFile(string fileId)
	    {
			Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("fileId", fileId);
            postParameters.Add("format", "cli");
			FILE_DOWNLOADS[fileId] = 0; //Percentage complete
			try
			{
				this.postDataToServer(FL_SERVER + "/file_interface/download", postParameters, true);
			}
			catch (Exception e)
			{
				throw new FilelockerException(e.Message);
			}
			return true;
	    }
		
		public void upload(byte[] imageBytes, string fileName, string fileNotes)
		{
			Dictionary<string, string> postParameters = new Dictionary<string, string>() 
			{
				{"fileName", fileName},
				{"fileNotes", fileNotes},
				{"scanFile", "false"},
				{"format", "cli"}
			};
			this.HttpUploadFile(FL_SERVER+"/file_interface/upload?format=cli", imageBytes, fileName, postParameters);
		}
		
		public List<KeyValuePair<string, string>> readServersFile()
		{
			var documents = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
			string filename = "known_servers.xml";
			StringBuilder serversXML = new StringBuilder("");
			using (StreamReader sr = new StreamReader(Path.Combine(documents, filename)))
            {
                String line;
                // Read and display lines from the file until the end of
                // the file is reached.
                while ((line = sr.ReadLine()) != null)
                {
                    serversXML.Append(line);
                }
            }
			
			XmlDocument doc = new XmlDocument();
            doc.LoadXml(serversXML.ToString());
			List<KeyValuePair<string, string>> knownServers = new List<KeyValuePair<string, string>>();
            foreach (XmlNode node in doc.ChildNodes)
            {
                if (node.Name == "filelocker_servers")
				{
					foreach (XmlNode filelockerServer in node)
					{
						string serverName = "";
						string serverURL = "";
						foreach (XmlNode filelockerServerAttribute in filelockerServer)
						{
							if (filelockerServerAttribute.Name.Equals("server_name"))
							{
								serverName = filelockerServerAttribute.InnerText;
							}
							else if (filelockerServerAttribute.Name.Equals("server_url"))
							{
								serverURL = filelockerServerAttribute.InnerText;
							}
						}
						knownServers.Add(new KeyValuePair<string, string>(serverName, serverURL));
					}
				}
            }
			return knownServers;
		}
		public void updateKnownServers()
		{
			WebResponse resp=null;
			Stream localStream = null;
			StringBuilder serversXML = new StringBuilder("");
			try
			{
				HttpWebRequest wr = (HttpWebRequest)WebRequest.Create("https://downloads.sourceforge.net/project/filelocker2/known_servers.xml?r=&ts=1309291508&use_mirror=master");
				wr.Timeout = 10000;
				resp = wr.GetResponse();
				var documents = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
				using (Stream responseStream = resp.GetResponseStream())
            	{
					int bytesProcessed = 0;
					string filename = "known_servers.xml";
					localStream = File.Create(Path.Combine(documents, filename));
					
					byte[] buffer = new byte[1024];
					int bytesRead;
				    do
				    {
						bytesRead = responseStream.Read(buffer, 0, buffer.Length);						
						localStream.Write(buffer, 0, bytesRead);
						bytesProcessed += bytesRead;
				    } 
					while (bytesRead > 0);
				}
			}
			catch(Exception e)
			{
				Console.WriteLine("Could not get list of servers: {0}", e.Message);
				throw new FilelockerException("Could not get list of servers: "+e.Message);				
			}
			finally
			{
				if (resp != null) resp.Close();
				if (localStream != null) localStream.Close();
			}
		}
	}
	
	public class FilelockerException : Exception
	{
		public FilelockerException(string message): base(message)
		{
			
		}
	}
}