using System;
using System.Collections.Generic;
using MonoTouch.UIKit;
using MonoTouch.Foundation;
namespace Filelocker
{
	class FilesDataSource : UITableViewSource
	{
		UINavigationController controller;
		List<KeyValuePair<string, List<FLFile>>> fileSectionKVPList;
		public FilesDataSource (UINavigationController navc, List<KeyValuePair<string, List<FLFile>>> fskvpl)
		{
			this.controller = navc;
			this.fileSectionKVPList = fskvpl;
		}
		
		public override int NumberOfSections(UITableView tableView)
		{
			return fileSectionKVPList.Count;
		}
		
		public override string TitleForHeader (UITableView tableView, int section)
		{
			return fileSectionKVPList[section].Key;
		}
		
		public override int RowsInSection(UITableView tableview, int section)
		{
			return fileSectionKVPList[section].Value.Count;
		}
		
		public override UITableViewCell GetCell (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
		{
			string cellidentifier = "Cell";
			var cell = tableView.DequeueReusableCell(cellidentifier);
			if (cell == null)
			{
				cell = new UITableViewCell(UITableViewCellStyle.Default, cellidentifier);
			}
			//indexPath.Section
			FLFile rowFile = fileSectionKVPList[indexPath.Section].Value[indexPath.Row];
			cell = new FileCell(rowFile, FilelockerConnection.Instance.USERID);
			
			return cell;
		} 
		
		public override void RowSelected (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
		{
			FLFile rowFile = fileSectionKVPList[indexPath.Section].Value[indexPath.Row];
			FileInfoView fivc = new FileInfoView(rowFile);
			controller.PushViewController(fivc, true);
		}
		
		public override void CommitEditingStyle(UITableView tableView, UITableViewCellEditingStyle editingStyle, NSIndexPath indexPath)
		{
			if (editingStyle == UITableViewCellEditingStyle.Delete)
			{
				FLFile editFile = fileSectionKVPList[indexPath.Section].Value[indexPath.Row];
				try
				{
					FilelockerConnection.Instance.deleteFile(editFile.fileId);
					fileSectionKVPList[indexPath.Section].Value.Remove(editFile);
					tableView.DeleteRows(new [] {indexPath}, UITableViewRowAnimation.Fade);
				}
				catch (FilelockerException fe)
				{
					((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Error Deleting File", fe.Message);
				}
			}
		}
	}
}

