using System;
using System.IO;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Net;
using System.Web;
using System.Windows.Forms;
using System.Xml;
using System.Configuration;
namespace WinFilelocker
{
    class Program
    {
        public static SettingsForm settingsForm = null;
        static void Main(string[] args)
        {
            NameValueCollection settings = ConfigurationManager.AppSettings;
            if (args.Length == 0)
            {
                if (settings["FilelockerHost"] == "" || settings["CLIKey"] == "" || settings["User"]=="")
                {
                    Application.Run(new RegisterForm());
                }
            }
           
            if (args.Length > 0)
            {
                if (args[0].Equals("upload"))
                {
                    string filePath = args[1];
                    CookieContainer cookies = new CookieContainer();
                    //add or use cookies
                    string name = System.Configuration.ConfigurationManager.AppSettings["OperatorName"];
                    string username = "";
                    string cliKey = "";
                    //postParameters = new Dictionary<string,string>();
                    //postParameters.Add("fileName", "uname");
                    //string outdata = UploadFileEx(filePath, "http://192.168.12.3:8080/file_interface/upload", "fileName", "image/pjpeg", postParameters, cookies);
                }
            }
        }

        public static Dictionary<string, Object> register(string userName, string password, string flServer)
        {
            //string userName = ConfigurationManager.AppSettings['User'];
            //string cliKey = ConfigurationManager.AppSettings['CLIKey'];
            //string flServer = ConfigurationManager.AppSettings['FilelockerHost'];

            Dictionary<string, string> postParameters = new Dictionary<string, string>();
            postParameters.Add("username", userName);
            postParameters.Add("password", password);
            postParameters.Add("format", "cli");
            string response = postDataToServer(flServer + "/cli_interface/register_client", postParameters);
            Dictionary<string, Object> responseDict = parseFilelockerResponse(response);
            if (((List<string>)responseDict["fMessages"]).Count == 0)
            {
                // Open App.Config of executable
                System.Configuration.Configuration config = ConfigurationManager.OpenExeConfiguration(ConfigurationUserLevel.None);
                // Add an Application Setting.
                config.AppSettings.Settings.Remove("FilelockerHost");
                config.AppSettings.Settings.Add("FilelockerHost", flServer);
                config.AppSettings.Settings.Remove("User");
                config.AppSettings.Settings.Add("User", userName);
                config.AppSettings.Settings.Remove("CLIKey");
                config.AppSettings.Settings.Add("CLIKey", (string)responseDict["data"]);
                // Save the configuration file.
                config.Save(ConfigurationSaveMode.Modified);
                // Force a reload of a changed section.
                ConfigurationManager.RefreshSection("appSettings");
            }
            else
            {
                ((List<string>)responseDict["fMessages"]).Add("The client configuration has not been updated");
            }
            return responseDict;
        }

        public static Dictionary<string, Object> parseFilelockerResponse(string response)
        {
            Dictionary<string, Object> formattedResponse = new Dictionary<string, Object>();
            List<string> sMessages = new List<string>();
            List<string> fMessages = new List<string>();
            string data = "";
            if (!response.StartsWith("Error:"))
            {
                XmlDocument doc = new XmlDocument();
                doc.LoadXml(response);
                foreach (XmlElement item in doc.GetElementsByTagName("info"))
                {
                    sMessages.Add(item.InnerText);
                }
                foreach (XmlElement item in doc.GetElementsByTagName("error"))
                {
                    fMessages.Add(item.InnerText);
                }
                foreach (XmlElement item in doc.GetElementsByTagName("data"))
                {
                    data = item.InnerText;
                }
            }
            else 
            {
                fMessages.Add(response); //This means that the response is already some kind of error message, not an XML response
            }
            formattedResponse.Add("sMessages", sMessages);
            formattedResponse.Add("fMessages", fMessages);
            formattedResponse.Add("data", data);
            return formattedResponse;
        }


        public static string postDataToServer(string server, Dictionary<string, string> postParameters)
        {
            //convert post parameters into URLencoded post data
            string serverResponse = "";
            string postData = "";
            foreach (string key in postParameters.Keys)
            {
                postData += System.Web.HttpUtility.UrlEncode(key) + "=" + System.Web.HttpUtility.UrlEncode(postParameters[key]) + "&";
            }
            ASCIIEncoding encoding = new ASCIIEncoding();
            byte[] data = encoding.GetBytes(postData);
            // Prepare web request...
            try
            {
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(server);
                request.Method = "POST";
                request.ContentType = "application/x-www-form-urlencoded";
                request.ContentLength = data.Length;
                Stream newStream = request.GetRequestStream();
                // Send the data.
                newStream.Write(data, 0, data.Length);
                newStream.Close();
                HttpWebResponse wResp = (HttpWebResponse)request.GetResponse();
                Stream responseStream = wResp.GetResponseStream();
                StreamReader responseReader = new StreamReader(responseStream);
                serverResponse += responseReader.ReadToEnd();
                wResp.Close();
            }
            catch (WebException we)
            {
                serverResponse = "Error: ";
                serverResponse += ((HttpWebResponse)we.Response).StatusDescription;
            }
            return serverResponse;
        }

        public static bool login(string username, string cliKey, string host, CookieContainer cookies)
        {
            HttpWebRequest webrequest = (HttpWebRequest)WebRequest.Create(host);
            return true;
        }

        public static string UploadFileEx( string uploadfile, string url, string fileFormName, string contenttype, Dictionary<string, string> getParameters, CookieContainer cookies)
        {
            if( (fileFormName== null) ||
                (fileFormName.Length ==0))
            {
                fileFormName = "file";
            }

            if( (contenttype== null) ||
                (contenttype.Length ==0))
            {
                contenttype = "application/octet-stream";
            }


            string getData = "?";
            foreach (string key in getParameters.Keys)
            {
                getData += System.Web.HttpUtility.UrlEncode(key) + "=" + System.Web.HttpUtility.UrlEncode(getParameters[key]) + "&";
            }
            Uri uri = new Uri(url+getData);


            string boundary = "----------" + DateTime.Now.Ticks.ToString("x");
            HttpWebRequest webrequest = (HttpWebRequest)WebRequest.Create(uri);
            webrequest.CookieContainer = cookies;
            webrequest.ContentType = "multipart/form-data; boundary=" + boundary;
            webrequest.Method = "POST";


            // Build up the post message header

            StringBuilder sb = new StringBuilder();
            sb.Append("--");
            sb.Append(boundary);
            sb.Append("\r\n");
            sb.Append("Content-Disposition: form-data; name=\"");
            sb.Append(fileFormName);
            sb.Append("\"; filename=\"");
            sb.Append(Path.GetFileName(uploadfile));
            sb.Append("\"");
            sb.Append("\r\n");
            sb.Append("Content-Type: ");
            sb.Append(contenttype);
            sb.Append("\r\n");
            sb.Append("\r\n");            

            string postHeader = sb.ToString();
            byte[] postHeaderBytes = Encoding.UTF8.GetBytes(postHeader);

            // Build the trailing boundary string as a byte array

            // ensuring the boundary appears on a line by itself

            byte[] boundaryBytes = 
                   Encoding.ASCII.GetBytes("\r\n--" + boundary + "\r\n");

            FileStream fileStream = new FileStream(uploadfile, 
                                        FileMode.Open, FileAccess.Read);
            long length = postHeaderBytes.Length + fileStream.Length + 
                                                   boundaryBytes.Length;
            webrequest.ContentLength = length;

            Stream requestStream = webrequest.GetRequestStream();

            // Write out our post header

            requestStream.Write(postHeaderBytes, 0, postHeaderBytes.Length);

            // Write out the file contents

            byte[] buffer = new Byte[checked((uint)Math.Min(4096, 
                                     (int)fileStream.Length))];
            int bytesRead = 0;
            while ( (bytesRead = fileStream.Read(buffer, 0, buffer.Length)) != 0 )
                requestStream.Write(buffer, 0, bytesRead);

            // Write out the trailing boundary

            requestStream.Write(boundaryBytes, 0, boundaryBytes.Length);
            WebResponse responce = webrequest.GetResponse();
            Stream s = responce.GetResponseStream();
            StreamReader sr = new StreamReader(s);

            return sr.ReadToEnd();
        }

        
    }
}
