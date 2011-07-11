using System;
using System.IO;
using System.Collections.Generic;
using System.Drawing;
using MonoTouch.UIKit;
using MonoTouch.Foundation;
namespace Filelocker
{
	public delegate void RowSelectedEventHandler (object sender, RowSelectedEventArgs args);
	public class RowSelectedEventArgs : EventArgs
	{
		public FLFile sFile { get; set; }
	}
	public class FileInfoViewDataSource : UITableViewSource
	{
		UISwitch sw;
		FLFile sourceFile;
		public event RowSelectedEventHandler ButtonRowSelected;
		public FileInfoViewDataSource (FLFile sourceFile)
		{
			this.sourceFile = sourceFile;
		}
		
		public override int NumberOfSections(UITableView tableView)
		{
			return 2;
		}
		
		public override string TitleForHeader (UITableView tableView, int section)
		{
			string title="";
			switch(section)
			{
				case 0:
					title = "File Information";
					break;
				case 1:
					title = "Actions";
					break;
			}
			return title;
		}
		
		public override int RowsInSection(UITableView tableview, int section)
		{
			if (section == 0)
			{
				return 3;
			}
			else if (section == 1)
			{
				return 2;
			}
			else 
			{
				return 0;
			}
		}
		
		public override UITableViewCell GetCell (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
		{
			string cellidentifier = "Cell";
			var cell = tableView.DequeueReusableCell(cellidentifier);
			if (cell == null)
			{
				cell = new UITableViewCell(UITableViewCellStyle.Subtitle, cellidentifier);
			}
			switch (indexPath.Section)
			{
				case 0:
					UIFont titleFont = UIFont.FromName ("Helvetica-Bold", 17);
					UIFont detailFont = UIFont.FromName ("Helvetica-Bold", 12);
					switch(indexPath.Row)
					{
						case 0:
							cell.TextLabel.Font = detailFont;				
							cell.DetailTextLabel.Font = titleFont;
							cell.TextLabel.Text = "File Name";
							cell.DetailTextLabel.Text = sourceFile.fileName;
							break;
						case 1:
							cell.TextLabel.Font = detailFont;				
							cell.DetailTextLabel.Font = titleFont;
							cell.TextLabel.Text = "File Size";
							cell.DetailTextLabel.Text = sourceFile.getFormattedSize();
							break;
						case 2:
							cell.TextLabel.Font = detailFont;
							cell.TextLabel.Text = "Download Notifications:";
							sw = new UISwitch (new RectangleF (198f, 12f, 94f, 27f));
							sw.On = sourceFile.fileNotifyOnDownload;
							sw.ValueChanged += delegate {
								try
								{
									Console.WriteLine("Hey, trying");
									FilelockerConnection.Instance.toggleFileNotifications(sourceFile.fileId, sw.On);
								}
								catch (FilelockerException fe)
								{
									((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Failed to Update", fe.Message);    
								}
								catch (Exception e)
								{
									((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Error: ", e.Message);    
								}
							};
							cell.AccessoryView = sw;
							break;
					}
					break;
				case 1:
					cell.TextLabel.Font = UIFont.FromName ("Helvetica-Bold", 20);
					cell.TextLabel.TextAlignment = UITextAlignment.Center;
					switch(indexPath.Row)
					{
						case 0:
							cell.TextLabel.Text = "Share";
							break;
						case 1:
							if (sourceFile.downloaded)
							{
								cell.TextLabel.Text = "Open";
								cell.AccessoryView = null; //Purge progress bar
							}
							else
							{
								cell.TextLabel.Text = "Download";
							}
							break;
					}
					break;
			}
			return cell;
		} 
		
		public override void RowSelected (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
		{
			switch(indexPath.Section)
			{
				case 0:
					break;
				case 1:
					switch(indexPath.Row)
					{
						case 0:
							//TODO: Make the controller do this
							//controller.PresentModalViewController(new FileShare(controller.sourceFile),true);
							break;
						case 1:
							if (sourceFile.downloaded)
							{
								//TODO: Make the controller do this
								//controller.PresentModalViewController(new FileViewer(strFilePath, controller.sourceFile.fileName), true);
								ButtonRowSelected (this, new RowSelectedEventArgs () { sFile = sourceFile });
								tableView.DeselectRow(indexPath, true);
							}
							else
							{
								//TODO: Call the download file event with the file as the argument 
							}
							//controller.controller.StartFileRefresh();
							break;
					}
					break;
			}
		}
	}
}

