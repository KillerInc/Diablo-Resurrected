// Offline save inspection and copy-only stash editing with the engine codec.
#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <vector>
#include <mpqfs/mpqfs.h>
#include "codec.h"
#include "game_mode.hpp"
#include "pack.h"
#include "pfile.h"
#include "utils/endian_read.hpp"
#include "utils/endian_write.hpp"
using namespace devilution;
static void Require(bool ok,const char *message){if(!ok)throw std::runtime_error(message);}
static std::vector<std::byte> Decode(const std::filesystem::path &path,const char *entry){
 auto archive=MpqArchive::Open(path.string().c_str());Require(bool(archive),"Cannot open archive");
 size_t size=0;auto data=ReadArchive(*archive,entry,&size);Require(bool(data),"Cannot decode archive entry");
 return {data.get(),data.get()+size};
}
static uint32_t Gold(const std::vector<std::byte>& data){
 Require(data.size()>=17&&data[0]==std::byte{0},"Unsupported stash version/size");
 const auto pages=LoadLE32(data.data()+5);Require(9ULL+204ULL*pages+8<=data.size(),"Invalid stash pages");
 const auto count=LoadLE32(data.data()+9+pages*204ULL);
 Require(17ULL+204ULL*pages+368ULL*count==data.size(),"Invalid Diablo stash item size");
 const auto value=LoadLE32(data.data()+1);Require(value<=uint32_t(INT32_MAX),"Invalid signed stash gold");return value;
}
static std::map<uint32_t,std::vector<std::byte>> Entries(const std::filesystem::path &path){
 auto archive=MpqArchive::Open(path.string().c_str());Require(bool(archive),"Cannot open verification archive");
 std::ifstream header(path,std::ios::binary);std::byte h[32];header.read(reinterpret_cast<char*>(h),32);
 Require(header&&LoadLE32(h+24)==MpqWriterHashTableSize,"Unsupported hash-table size");
 std::map<uint32_t,std::vector<std::byte>> result;
 for(uint32_t hash=0;hash<MpqWriterHashTableSize;++hash)if(archive->HasFileHash(hash)){
  const auto size=archive->GetFileSizeFromHash(hash);std::vector<std::byte> bytes(size);
  mpqfs_stream_t *stream=nullptr;Require(mpqfs_stream_open_from_hash(archive->handle(),hash,&stream)==MPQFS_OK,"Cannot open hashed entry");
  size_t read=0;const auto status=mpqfs_stream_read(stream,bytes.data(),size,&read);mpqfs_stream_close(stream);
  Require(status==MPQFS_OK&&read==size,"Cannot read hashed entry");result.emplace(hash,std::move(bytes));
 }
 return result;
}
int main(int argc,char **argv){try{
 gbIsSpawn=false;gbIsMultiplayer=false;gbIsHellfire=false;
 Require(argc>=3,"Usage: inspect PROFILE | quarter-copy INPUT OUTPUT | verify INPUT OUTPUT");
 const std::string mode=argv[1];
 if(mode=="inspect"){
  for(const auto &entry:std::filesystem::directory_iterator(argv[2])){
   const auto name=entry.path().filename().string();
   if(name.rfind("single_",0)==0&&entry.path().extension()==".sv"){
    const auto data=Decode(entry.path(),"hero");Require(data.size()==sizeof(PlayerPack),"Hero format differs from this engine");
    PlayerPack hero{};std::memcpy(&hero,data.data(),sizeof(hero));
    std::cout<<"HERO "<<name<<" name="<<std::string(hero.pName,strnlen(hero.pName,sizeof(hero.pName)))<<" level="<<unsigned(hero.pLevel)<<" class="<<unsigned(hero.pClass)<<'\n';
   }
  }
  const auto data=Decode(std::filesystem::path(argv[2])/"stash.sv","spstashitems");
  std::cout<<"STASH gold="<<Gold(data)<<" max="<<INT32_MAX<<" quarter="<<INT32_MAX/4<<" shared=single_player\n";return 0;
 }
 Require(argc==4,"Input and output paths required");
 const std::filesystem::path before=argv[2],after=argv[3];
 const auto original=Decode(before,"spstashitems");const uint32_t previous=Gold(original),target=INT32_MAX/4;
 if(mode=="quarter-copy"){
  Require(!std::filesystem::exists(after),"Output must be a new working copy");
  std::filesystem::copy_file(before,after);
  auto modified=original;WriteLE32(modified.data()+1,target);
  const auto encodedSize=codec_get_encoded_len(modified.size());std::vector<std::byte> encoded(encodedSize);
  std::copy(modified.begin(),modified.end(),encoded.begin());codec_encode(encoded.data(),modified.size(),encoded.size(),pfile_get_password());
  {MpqWriter writer(after.string());Require(writer.WriteFile("spstashitems",encoded.data(),encoded.size()),"Stash write failed");}
 }else Require(mode=="verify","Unknown mode");
 const auto changed=Decode(after,"spstashitems");Require(Gold(changed)==target&&changed.size()==original.size(),"Gold verification failed");
 for(size_t i=0;i<original.size();++i)if(i<1||i>=5)Require(original[i]==changed[i],"A non-gold stash byte changed");
 auto a=MpqArchive::Open(before.string().c_str());auto b=MpqArchive::Open(after.string().c_str());Require(bool(a)&&bool(b),"Archive verification failed");
 const auto oldHash=a->FindHash("spstashitems"),newHash=b->FindHash("spstashitems");Require(oldHash==newHash,"Stash hash placement changed");
 auto oldEntries=Entries(before),newEntries=Entries(after);Require(oldEntries.size()==newEntries.size(),"Archive member count changed");
 for(const auto &[hash,bytes]:oldEntries)if(hash!=oldHash)Require(newEntries.contains(hash)&&newEntries.at(hash)==bytes,"Another archive member changed");
 std::cout<<"VERIFIED previous="<<previous<<" gold="<<target<<" decoded_bytes="<<original.size()<<" members="<<oldEntries.size()<<" all_non_gold_bytes_preserved=1\n";
 return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
